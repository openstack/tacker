..
      Copyright 2014-2015 OpenStack Foundation
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

=========================
Tacker Installation Guide
=========================

Installation
------------

For Tacker to work, the system consists of two parts, one is tacker system
and another is VIM systems. Tacker system can be installed
(here just some ways are listed):

* via DevStack, which is usually used by developers
* via Tacker source code manually
* via Kolla installation


.. toctree::
   :maxdepth: 1

   devstack.rst
   manual_installation.rst
   kolla.rst


Target VIM installation
-----------------------

Most of time, the target VIM existed for Tacker to manage. This section shows
us how to prepare a target VIM for Tacker.

.. toctree::
   :maxdepth: 1

   openstack_vim_installation.rst
   kubernetes_vim_installation.rst
