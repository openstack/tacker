=======================
Legacy Tacker Use Cases
=======================

.. warning::
    Legacy Tacker features excluding VIM feature are deprecated
    and will be removed in the first major release after the Tacker server
    version 9.0.0 (2023.1 Antelope release).

VIM
---

Enable Multi Site
^^^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   multisite_vim_usage_guide

VNFFG
-----

Deploy
^^^^^^

.. toctree::
   :maxdepth: 1

   vnffg_usage_guide
   vnffg_usage_guide_advanced

Update
^^^^^^

.. toctree::
   :maxdepth: 1

   dynamic_vnffg_usage_guide

NS
--

Deploy
^^^^^^

.. toctree::
   :maxdepth: 1

   nsd_usage_guide

VNF
---

Deploy
^^^^^^

VM
~~

.. toctree::
   :maxdepth: 1

   vnfm_usage_guide
   placement_policy_usage_guide
   containerized_vnf_usage_guide


Container
~~~~~~~~~

.. toctree::
   :maxdepth: 1

   containerized_vnf_usage_guide

Scale
^^^^^

.. toctree::
   :maxdepth: 1

   scale_usage_guide

Monitor Driver
^^^^^^^^^^^^^^


Overview
~~~~~~~~

.. toctree::
   :maxdepth: 1

   ../contributor/monitor-api

Zabbix
~~~~~~

.. toctree::
   :maxdepth: 1

   ../contributor/zabbix-plugin

.. TODO(h-asahina): add `Ping.
  * https://etherpad.opendev.org/p/tacker-wallaby-revise-docs


Policy-Action Driver
^^^^^^^^^^^^^^^^^^^^

Overview
~~~~~~~~

.. toctree::
   :maxdepth: 1

   ../contributor/policy_actions_framework

.. TODO(h-asahina): add `AutoHeal` `AutoScale`, `Respawn` and `Log`.
  * https://etherpad.opendev.org/p/tacker-wallaby-revise-docs

Placement-Aware Deployment
---------------------------------

.. toctree::
   :maxdepth: 1

   enhanced_placement_awareness_usage_guide

Collaboration with Other Projects
---------------------------------

.. toctree::
   :maxdepth: 1

   ../contributor/encrypt_vim_auth_with_barbican
   ../reference/block_storage_usage_guide
   alarm_monitoring_usage_guide
   ../reference/reservation_policy_usage_guide
