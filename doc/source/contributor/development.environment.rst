..
      Copyright 2010-2015 United States Government as represented by the
      Administrator of the National Aeronautics and Space Administration.
      All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

Setting Up a Development Environment
====================================

This page describes how to setup a working Python development
environment that can be used in developing Tacker on Ubuntu, Fedora or
Mac OS X. These instructions assume you're already familiar with
Git and Gerrit, which is a code repository mirror and code review toolset
, however if you aren't please see `this Git tutorial`_ for an introduction
to using Git and `this guide`_ for a tutorial on using Gerrit and Git for
code contribution to OpenStack projects.

.. _this Git tutorial: http://git-scm.com/book/en/Getting-Started
.. _this guide: https://docs.openstack.org/infra/manual/developers.html#development-workflow

If you want to be able to run Tacker in a full OpenStack environment,
you can use the excellent `DevStack`_ project to do so. There is a wiki page
that describes `setting up Tacker using DevStack`_.

.. _DevStack: https://opendev.org/openstack/devstack
.. _setting up Tacker using Devstack: https://docs.openstack.org/tacker/latest/install/devstack.html

Getting the code
----------------

Grab the code::

    git clone https://opendev.org/openstack/tacker.git
    cd tacker


.. include:: ../../../TESTING.rst

Linting
-------

Tacker project supports the configuration of `Pylint`_, a lint tool for
Python code.

You can get Pylint CLI tool from PyPI:

.. code-block:: console

    $ pip install pylint

Then you can check your code with Pylint like:

.. code-block:: console

    $ pylint path/to/code

If you want to check the entire Tacker code:

.. code-block:: console

    $ pylint tacker/

``.pylintrc`` in Tacker repository root is a configuration file of Pylint.

If you want to check Pylint messages, detailed CLI configurations
and configurations in ``.pylintrc``, please refer to
`Pylint official reference`_.

.. _Pylint: https://pylint.org/
.. _Pylint official reference: https://pylint.pycqa.org/en/latest/
