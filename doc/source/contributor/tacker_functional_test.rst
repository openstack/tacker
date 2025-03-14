..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
  License.

 http://creativecommons.org/licenses/by/3.0/legalcode


===============================
Functional testcases for tacker
===============================

Purpose of functional testcases is to verify various functionality of tacker
features. From tacker home directory, testcases are located at
tacker/tests/functional.

Writing a testcase:A testcase is written by declaring a class name derived from
class base.BaseTackerTest. BaseTackerTest is class declared in
tacker/tests/functional/base.py.

A testcase body typically looks as below:


.. code-block:: python

 class testClassName(base.BaseTackerTest):

     //setup

     //Testcase operations

     //validations or asserts

     //cleanup


In above example test class 'testClassName' is derived from
base.BaseTackerTest. Testcases typically has sections to setup, test, validate
results and finally cleanup.

Input yaml files: These are input files used in testcases for operations like
create vnfd or create vnf. The location of files is samples/tests/etc/samples/.

requirements.txt and test-requirements.txt : The file requirements.txt and
test-requirements.txt lists all the packages needed for functional test.
These packages are installed during devstack installation. If there are any
new packages needed for functional test make sure they are added in
test-requirements.txt.

Asserting values in testcase: The base class BaseTackerTest
inherits base.TestCase which has inbuild assert functions which can be used in
testcase.
Eg: assertIsNotNone, assertEqual

Tacker-client: In base.py we instantiate tackerclient object which has apis to
create/delete/list vnfd/vnf once given the necessary parameters.
Verify tackerclient/v1_0/client.py for all the tacker related apis supported.


Important guidelines to follow:
===============================

* Install test-requirements.txt with below command:

.. code-block:: console

  pip install -r test-requirements.txt


* It is important that the test case executed leaves the
  system in the same state it was prior to test case execution
  and not leave any stale data on system as this might affect
  other test cases.
* There should not be any dependencies between testcases
  which assume one testcase should be executed and be passed
  for second testcase.
* Testcases in tox environment may be executed in parallel.
  The order in which the testcases are executed may vary
  between two environments.
* The code added should meet pep8 standards. This can be verified with
  following command and ensuring the code does not return any errors.

.. code-block:: console

  tox -e pep8


Execution of testcase:
======================

* Install tacker server via devstack installation, which registers
  tacker service and endpoint, creates "nfv_user" and "nfv" project,
  and registers default VIM with the created user and project.

* From tacker directory, specific testcases can be executed using
  following commands:

.. code-block:: console

  tox -e functional tacker.tests.functional.xxx.yyy.<testcase>


Multi-node configuration for testing
------------------------------------

For the Zuul environment that runs functional test, install
tacker server via devstack installation in multi-node configuration.

.. note::

  Not all functional tests require a multi-node configuration.
  Many tests can be run in an all-in-one mode.
  See :doc:`/install/devstack` for installing all-in-one mode.


The steps to create an environment with a multi-node configuration
similar to Zuul(controller/controller-tacker/compute1/compute2) are as
follows.
Here is a sample case that does not use k8s.
Create four virtual machine (VM) environments each with IP addresses
and host names, for example:

- 192.168.56.11 controller
- 192.168.56.12 controller-tacker
- 192.168.56.13 compute1
- 192.168.56.14 compute2

From above four hosts, DevStack on the controller host must be built first.
Once completed, proceed with the remaining three hosts:
controller-tacker, compute1, and compute2.
The order of building Devstack on these three hosts is not important,
and you can build them simultaneously if desired.
To build DevStack on each host, run the script ./stack.sh.

Here is a sample case of using k8s.
Create four virtual machine (VM) environments each with IP addresses
and host names, for example:

- 192.168.56.21 controller
- 192.168.56.22 controller-tacker
- 192.168.56.23 controller-k8s

From above four hosts, DevStack on the controller host must be built first.
Once completed, proceed with the remaining three hosts: controller-tacker
and controller-k8s.
The order of building Devstack on these three hosts is not important,
and you can build them simultaneously if desired.
To build DevStack on each host, run the script ./stack.sh.

Regarding the specs of your machine,
see `Devstack`_ or :doc:`/install/devstack` for details on the OS
and Linux distribution to use.

For not using k8s
^^^^^^^^^^^^^^^^^

#. Preparation

   * Prepare 4VMs that meet the following criteria

     .. list-table::
        :widths: 60 150
        :header-rows: 1

        * - Criteria
          - Recommended
        * - CPU
          - 4 cores or more
        * - RAM
          - 16 GB or more
        * - Storage
          - 32 GB or more

   * Create stack user on each VM

     .. code-block:: console

       $ sudo useradd -s /bin/bash -d /opt/stack -m stack
       $ sudo chmod +x /opt/stack
       $ echo "stack ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/stack


   * Download devstack on each VM

     .. code-block:: console

       $ git clone https://opendev.org/openstack/devstack


#. Create controller node

   * Create the following local.conf on controller node

     .. code-block:: console

       $ cd devstack
       $ vi local.conf


     .. literalinclude:: ../../../devstack/multi-nodes/openstack/local.conf.controller
         :language: ini


   * Execute installation script

     .. code-block:: console

       $ ./stack.sh


#. Create controller-tacker node

   * Create the following local.conf on controller-tacker node

     .. code-block:: console

       $ cd devstack
       $ vi local.conf


     .. literalinclude:: ../../../devstack/multi-nodes/openstack/local.conf.controller-tacker
         :language: ini


   * Execute installation script

     .. code-block:: console

       $ ./stack.sh


#. Create compute1 node

   * Create the following local.conf on compute1 node

     .. code-block:: console

       $ cd devstack
       $ vi local.conf


     .. literalinclude:: ../../../devstack/multi-nodes/openstack/local.conf.compute1
         :language: ini


   * Execute installation script

     .. code-block:: console

       $ ./stack.sh


#. Create compute2 node

   * Create the following local.conf on compute2 node

     .. code-block:: console

       $ cd devstack
       $ vi local.conf


     .. literalinclude:: ../../../devstack/multi-nodes/openstack/local.conf.compute2
         :language: ini


   * Execute installation script

     .. code-block:: console

       $ ./stack.sh

For using k8s
^^^^^^^^^^^^^

#. Preparation

   * Prepare 3VMs that meet the following criteria

     .. list-table::
        :widths: 60 150
        :header-rows: 1

        * - Criteria
          - Recommended
        * - CPU
          - 4 cores or more
        * - RAM
          - 16 GB or more
        * - Storage
          - 32 GB or more

   * Create stack user on each VM

     .. code-block:: console

       $ sudo useradd -s /bin/bash -d /opt/stack -m stack
       $ sudo chmod +x /opt/stack
       $ echo "stack ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/stack


   * Download devstack on each VM

     .. code-block:: console

       $ git clone https://opendev.org/openstack/devstack


#. Create controller node

   * Create the following local.conf on controller node

     .. code-block:: console

       $ cd devstack
       $ vi local.conf


     .. literalinclude:: ../../../devstack/multi-nodes/k8s/local.conf.controller
         :language: ini


   * Execute installation script

     .. code-block:: console

       $ ./stack.sh


#. Create controller-tacker node

   * Create the following local.conf on controller-tacker node

     .. code-block:: console

       $ cd devstack
       $ vi local.conf


     .. literalinclude:: ../../../devstack/multi-nodes/k8s/local.conf.controller-tacker
         :language: ini


   * Execute installation script

     .. code-block:: console

       $ ./stack.sh


#. Create controller-k8s node

   * Create the following local.conf on controller-k8s node

     .. code-block:: console

       $ cd devstack
       $ vi local.conf


     .. literalinclude:: ../../../devstack/multi-nodes/k8s/local.conf.controller-k8s
         :language: ini


   * Execute installation script

     .. code-block:: console

       $ ./stack.sh

     .. note::

       Pre-settings may be required to install Kubernetes.
       See `Kubernetes documentation`_ for the target version for details.
       For example, the following settings are required for Kubernetes 1.30.5.

       .. code-block:: console

         $ sudo modprobe overlay
         $ sudo modprobe br_netfilter
         $ cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
         net.bridge.bridge-nf-call-ip6tableis=1
         net.bridge.bridge-nf-call-iptables=1
         net.ipv4.ip_forward=1
         EOF
         $ sudo sysctl --system


Settings
^^^^^^^^

Several settings are required to run the functional tests (FT).
We provide shell script files that implement those settings.
See :doc:`/reference/script_ft_v1` for how to use them.
Running these shell script files will complete the settings
for running following functional tests (FT).

* tacker-ft-legacy-vim
* tacker-ft-v1-vnfpkgm
* tacker-ft-v1-k8s
* tacker-ft-v1-tosca-vnflcm
* tacker-ft-v1-userdata-vnflcm


Committing testcase and opening a review:
=========================================

* Once testcase is added in local setup, commit the testcase and open for
  review using below guidelines:
  https://docs.openstack.org/infra/manual/developers.html


Sample testcase:
================
* Check sample tests under following directory:
  https://opendev.org/openstack/tacker/src/branch/master/tacker/tests/functional/


.. _Devstack: https://docs.openstack.org/devstack/latest/
.. _Kubernetes documentation:
  https://kubernetes.io/docs/setup/production-environment/container-runtimes/#install-and-configure-prerequisites
