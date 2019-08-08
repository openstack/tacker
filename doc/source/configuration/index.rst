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

==========================
Tacker Configuration Guide
==========================

The static configuration for tacker lives in three main files:
``api-paste.ini``, ``tacker.conf`` and ``policy.json``.
These are described below. For a bigger picture view on configuring
tacker to solve specific problems.

Configuration
-------------

* :doc:`API Paste ini <api-paste.ini>`: A complete reference of
  api-paste.ini available in the ``api-paste.ini`` file.

* :doc:`Config Reference <config>`: A complete reference of all
  configuration options available in the ``tacker.conf`` file.

* :doc:`Sample Config File <sample_config>`: A sample config
  file with inline documentation.

Policy
------

Tacker, like most OpenStack projects, uses a policy language to restrict
permissions on REST API actions.

* :doc:`Policy Reference <policy>`: A complete reference of all
  policy points in tacker and what they impact.

* :doc:`Sample Policy File <sample_policy>`: A sample tacker
  policy file with inline documentation.

.. # NOTE(bhagyashris): This is the section where we hide things that we don't
   # actually want in the table of contents but sphinx build would fail if
   # they aren't in the toctree somewhere.
.. toctree::
   :hidden:

   api-paste.ini
   policy
   sample_policy
   config
   sample_config
