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

For Tacker to work, the system consists of two parts:

* Tacker system
* VIM systems

Refer following installation procedures for both of these systems:

#. Tacker Installation

   Tacker can be installed using following methods:

   (here just some ways are listed)

   .. toctree::
      :maxdepth: 1

      Install via Devstack <devstack.rst>
      Manual Installation <manual_installation.rst>
      Install via Kolla Ansible <kolla.rst>

#. Target VIM Installation

   Most of the time, the target VIM already exists for Tacker to manage.
   In case the target VIM does not exist, this section shows how to prepare a
   target VIM for Tacker to manage.

   .. toctree::
      :maxdepth: 1

      Openstack VIM Installation <https://docs.openstack.org/install-guide/index.html>
      Kubernetes VIM Installation <kubernetes_vim_installation.rst>
