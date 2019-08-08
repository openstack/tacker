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

The Tacker service is configured in the ``/etc/tacker/tacker.conf`` file.
These are described below.

The sample configuration can also be viewed in :download:`file form
</_extra/tacker.conf.sample>`.

.. important::

   The sample configuration file is auto-generated from tacker when this
   documentation is built. You must ensure your version of tacker matches the
   version of this documentation.

.. literalinclude:: /_extra/tacker.conf.sample

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

   policy
   sample_policy
