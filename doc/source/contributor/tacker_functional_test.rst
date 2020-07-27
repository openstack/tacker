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
tacker/tests/functional/vnfd/base.py.

A testcase body typically looks as below:


.. code-block:: python

 class vnfClassName(base.BaseTackerTest):

   def test_create_delete(self):

     //Testcase operations

     //validations or asserts

     //cleanup


In above example test class 'vnfClassName' is derived from
base.BaseTackerTest. Testcases typically has sections to setup, test, validate
results and finally cleanup.

Input yaml files: These are input files used in testcases for operations like
create vnfd or create vnf. The location of files is tacker/tests/etc/samples/.

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

* Under tacker project dir, to prepare function test env via:

.. code-block:: console

  ./tools/prepare_functional_test.sh

* From tacker directory, all function testcases can be executed using
  following commands:

.. code-block:: console

  tox -e functional

* Or from tacker directory, specific testcases can be executed using
  following commands:

.. code-block:: console

  tox -e functional tacker.tests.functional.xxx.yyy.<testcase>


Committing testcase and opening a review:
=========================================

* Once testcase is added in local setup, commit the testcase and open for
  review using below guidelines:
  https://docs.openstack.org/infra/manual/developers.html

Sample testcase:
================
* Check sample tests under following directory:
  https://opendev.org/openstack/tacker/src/branch/master/tacker/tests/functional/
