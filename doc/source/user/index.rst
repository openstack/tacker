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

=================
Tacker User Guide
=================

Getting Started
---------------

.. toctree::
   :maxdepth: 1

   ../install/etsi_getting_started
   ../install/legacy_getting_started

.. TODO(h-asahina): add `Getting started with ETSI NFV-SOL Tacker`
  * https://etherpad.opendev.org/p/tacker-wallaby-revise-docs

Overview
--------

.. toctree::
   :maxdepth: 2

   introduction
   architecture
   resources



Use Case Guide
--------------

.. warning::
    Legacy Tacker features excluding VIM feature are deprecated
    and will be removed in the first major release after the Tacker server
    version 9.0.0 (2023.1 Antelope release).

.. toctree::
   :maxdepth: 1

   etsi_use_case_guide
   legacy_use_case_guide
   oauth2_usage_guide
   oauth2_mtls_usage_guide
   fault_notification_use_case_guide
   prometheus_plugin_use_case_guide
   db_migration_tool_usage_guide
   enhanced_tacker_policy_usage_guide
