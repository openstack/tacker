..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
  License.

 http://creativecommons.org/licenses/by/3.0/legalcode


===============================
Compliance testcases for tacker
===============================

Purpose of compliance testcases is to verify various functionality of
tacker api by using NFV TST code. From tacker home directory, testcases
are located at tacker/tests/compliance.

What is compliance test
=======================

Compliance tests are assessments used in the software development process.
Also known as conformance tests, these assessments confirm whether the
software meets particular standards before its production.

Whereas, the purpose of functional tests is to test each function of the
software application, by providing appropriate input, verifying the output
against the functional requirements.

About NFV API Conformance Test Specification (NFV-TST 010)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `api-tests`_ repository hosts
`ETSI NFV API Conformance test specification`_ for the APIs defined in
ETSI NFV GS SOL002, SOL003, SOL005. Currently available versions for
NFV API Conformance test specification are v2.4.1 (published), v2.6.1
(published), v2.7.1 (published) and v3.3.1(under development).

The Test Specification is built as a collection of Robot Framework Test
Description. Robot Framework is a generic test automation framework for
acceptance testing and acceptance test-driven development.

Tacker Compliance Test Composition
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This diagram briefly describe how compliance testing works.

Overview of testing by Robot Framework and ETSI NFV-TST010 test codes:

.. code-block:: console

   +---------------------------------------------------------------------------+
   |                                                                           |
   |                                                                           |
   |                                                                           |
   |             +-----------------------------------------------+             |
   |             | Tacker repository                             |             |
   |             |  +----------------+   +-------------------+   |             |
   |             |  | Community robot|   |Zuul configuration |   |             |
   |             |  | test code      |   |.zuul.yaml         |   |             |
   |             |  |                |   +-------------------+   |             |
   |             |  +----------------+                           |             |
   |             |                           +---------------+   |             |
   |             |  +----------------+       |playbook       |   |             |
   |             |  |testitem.robot  |       |runrobot.yaml  |   |             |
   |             |  +----------------+       +---------------+   |             |
   |             +-----------------------------------------------+             |
   |                                                         |                 |
   |          +-------------+   download (pip)               |                 |
   |          |             |   Robot framework              |                 |
   |          | python      +----------------------------+   |                 |
   |          | repository  |                            |   |                 |
   |          |             |                            |   |                 |
   |          +-------------+                            |   |                 |
   |                                                     v   v                 |
   |      +-----------------+  download                  ++---+-+              |
   |      |                 |  robot test code           |      |              |
   |      | ETSI repository +--------------------------->+ Zuul |              |
   |      | api-tests       |                            |      |              |
   |      |                 |      +---------------------+      +---+          |
   |      +-----------------+      |                     +------+   |          |
   |                               |                                |          |
   |                               | execute               execute  |          |
   |                               v                                v          |
   |                        +------+-----+             +------------+--+       |
   |                        |            |             |               |       |
   |                        | Robot      |    test     | Tacker        |       |
   |                        | framework  +------------>+ (devstack)    |       |
   |                        |            |             |               |       |
   |                        +------------+             +---------------+       |
   |                                                                           |
   |                                                                           |
   +---------------------------------------------------------------------------+

.. note::
   * **testitem.robot** is a list of test cases selected from the test code
     released by ETSI NFV-TST.
   * **playbook runrobot.yaml** install robot framework, download test code
     from `api-tests`_ repository and execute test with the above test list.


How to create Test Cases
========================

Precondition for Compliance Test
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**requirements.txt** : The file ``requirements.txt`` is present in api-tests
repository. It is cloned at time of compliance test execution and lists all
the packages needed for compliance test. These packages are installed during
execution of compliance test.

Implementation of test case
^^^^^^^^^^^^^^^^^^^^^^^^^^^

A testcase is written by declaring a class name derived from class
BaseVNFLifecycleManagementTest(base.BaseComplSolTest).
BaseComplSolTest is class declared in
``tacker/tests/compliance/sol003/base.py``.

A testcase body typically looks as below:

.. code-block:: python

 class VNFInstancesTest(BaseVNFLifecycleManagementTest):
    @classmethod
    def setUpClass(cls):
        cls.resource = 'VNFInstances'

        super(VNFInstancesTest, cls).setUpClass()

    def test_post_create_new_vnfinstance(self):

     //Testcase operations

     //validations or asserts


In above example test class 'VNFInstancesTest' is derived from
BaseVNFLifecycleManagementTest. Testcases typically has sections
to setup, test, validate results and finally cleanup.

Other Test Implementation
^^^^^^^^^^^^^^^^^^^^^^^^^

**Tacker-client** : Tackerclient object is instantiated in tacker/tests/
compliance/base.py which has apis to create/delete/list vnfd/vnf once
given the necessary parameters. Verify ``tackerclient/v1_0/client.py`` for
all the tacker related apis supported.

**Input yaml files** : These are input files used in testcases for operations
like create vnfd or create vnf.
The location of files is ``samples/tests/etc/samples/``.

**Asserting values in testcase** : The base class BaseTackerTest inherits base.
TestCase which has inbuilt assert functions which can be used in testcase.
example: assertIsNotNone, assertEqual

Steps to change TST's code version
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In Tacker's code, **2.6.1-fix-plu** api-tests version is check-in by default.

The NFV API Conformance test specification is available in the following
versions:

* v2.4.1
* v2.6.1
* v2.7.1
* v2.8.1
* v3.3.1
* v3.5.1
* v3.6.1

To change the version execute the below steps:

1. Open ``<tacker_route_directory>/tacker/tox.ini`` file in any editor.

2. Under [testenv:dsvm-compliance-sol-api] section in **commands_pre** while
   doing checkout of api-tests mention desired TST's code version.

   .. code-block:: console

      git -C api-tests checkout <desired_version>

   .. note::
      For desired_version please refer this url:
      https://forge.etsi.org/rep/nfv/api-tests/-/branches


Important guidelines to follow
==============================

* It is important that the test case executed leaves the
  system in the same state it was prior to test case execution
  and not leave any stale data on system as this might affect
  other test cases.

* There should not be any dependencies between testcases
  which assume one testcase should be executed and be passed
  for second testcase.

* The code added should meet pep8 standards. This can be verified with
  the following command and ensuring the code does not return any errors.

  .. code-block:: console

     tox -e pep8


Execution of testcase
=====================

* Install tacker server via devstack installation, which registers
  tacker service and endpoint, creates "nfv_user" and "nfv" project,
  and registers default VIM with the created user and project.

* From tacker directory, all compliance testcases can be executed using
  the following command:

  .. code-block:: console

     tox -e dsvm-compliance-sol-api

* Or from tacker directory, specific testcases can be executed using
  the following command:

  .. code-block:: console

     tox -e dsvm-compliance-sol-api tacker.tests.compliance.xxx.yyy.<testcase>


How to proceed when the test fails
==================================

* If test case fails check its logs.

* For example for 'GET_information_about_multiple_VNF_instances'
  test logs can be checked at below location:

  .. code-block:: console

     tacker/.tox/dsvm-compliance-sol-api/log/SOL003/VNFLifecycleManagement-API
     /VNFInstances/GET_information_about_multiple_VNF_instances

* Compliance test may also get failed due to code problem at
  NFV API Conformance test repository, then analyse the NFV-TST
  code locally.


Committing testcase and opening a review
========================================

Once testcase is added in local setup, commit the testcase and open for
review using below guidelines

https://docs.openstack.org/infra/manual/developers.html


Sample testcase
===============

Check sample tests under the following directory

https://opendev.org/openstack/tacker/src/branch/master/tacker/tests/compliance/

.. _api-tests : https://forge.etsi.org/rep/nfv/api-tests
.. _ETSI NFV API Conformance test specification : https://forge.etsi.org/rep/nfv/api-tests/-/wikis/NFV-API-Conformance-Test-Specification
