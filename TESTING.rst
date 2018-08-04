Testing Tacker
==============

Overview
--------

The unit tests are meant to cover as much code as possible and should
be executed without the service running. They are designed to test
the various pieces of the tacker tree to make sure any new changes
don't break existing functionality.

The functional tests are intended to validate actual system
interaction.  Mocks should be used sparingly, if at all.  Care
should be taken to ensure that existing system resources are not
modified and that resources created in tests are properly cleaned
up.

Development process
-------------------

It is expected that any new changes that are proposed for merge
come with tests for that feature or code area. Ideally any bugs
fixes that are submitted also have tests to prove that they stay
fixed!  In addition, before proposing for merge, all of the
current tests should be passing.

Running unit tests with tox
---------------------------

Before submitting a patch for review you should always ensure all
test pass; a tox run is triggered by the Zuul gate executed on
gerrit for each patch pushed for review.

With this mechanism you can either run the tests in the standard
environment or create a virtual environment to run them in.

By default after running all of the tests, any pep8 errors
found in the tree will be reported.

Note that the tests can use a database, see ``tools/tests-setup.sh``
on how the databases are set up in the OpenStack CI environment.

Tacker, like other OpenStack projects, uses `tox`_ for managing the virtual
environments for running test cases. It uses `stestr`_ for managing the running
of the test cases.

Tox handles the creation of a series of `virtualenvs`_ that target specific
versions of Python (2.7, 3.5, etc). stestr handles the parallel execution
of series of test cases as well as the tracking of long-running tests and
other things.

Running unit tests is as easy as executing this in the root directory of the
Tacker source code::

    tox

For more information on the standard Tox-based test infrastructure used by
OpenStack and how to do some common test/debugging procedures with stestr,
see at: https://governance.openstack.org/tc/reference/pti/python.html

.. _stestr: https://stestr.readthedocs.io/en/latest/
.. _tox: https://tox.readthedocs.io/en/latest/
.. _virtualenvs: https://pypi.org/project/virtualenv/


Running individual tests
~~~~~~~~~~~~~~~~~~~~~~~~

For running individual test modules or cases, you just need to pass
the dot-separated path to the module you want as an argument to it.

For executing a specific test case, specify the name of the test case
class separating it from the module path with a colon.

For example, the following would run only the TestVNFMPlugin tests from
tacker/tests/unit/vm/test_plugin.py::

      $ ./tox tacker.tests.unit.vm.test_plugin:TestVNFMPlugin

Debugging
---------

It's possible to debug tests in a tox environment::

    $ tox -e venv -- python -m testtools.run [test module path]

Tox-created virtual environments (venv's) can also be activated
after a tox run and reused for debugging::

    $ tox -e venv
    $ . .tox/venv/bin/activate
    $ python -m testtools.run [test module path]

Tox packages and installs the tacker source tree in a given venv
on every invocation, but if modifications need to be made between
invocation (e.g. adding more pdb statements), it is recommended
that the source tree be installed in the venv in editable mode::

    # run this only after activating the venv
    $ pip install --editable .

Editable mode ensures that changes made to the source tree are
automatically reflected in the venv, and that such changes are not
overwritten during the next tox run.
