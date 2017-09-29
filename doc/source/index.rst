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

===============================
Welcome to Tacker Documentation
===============================

Tacker is an OpenStack service for NFV Orchestration with a general purpose
VNF Manager to deploy and operate Virtual Network Functions (VNFs) and
Network Services on an NFV Platform. It is based on ETSI MANO Architectural
Framework.

Installation
============

For Tacker to work, the system consists of two parts, one is tacker system
and another is VIM systems. Tacker system can be installed
(here just some ways are listed):

* via devstack, which is usually used by developers
* via Tacker source code manually
* via Kolla installation


.. toctree::
   :maxdepth: 1

   install/kolla.rst
   install/devstack.rst
   install/manual_installation.rst

Target VIM installation
=======================

Most of time, the target VIM existed for Tacker to manage. This section shows
us how to prepare a target VIM for Tacker.

.. toctree::
   :maxdepth: 1

   install/openstack_vim_installation.rst
   install/kubernetes_vim_installation.rst


Getting Started
===============

.. toctree::
   :maxdepth: 1

   install/getting_started.rst
   install/deploy_openwrt.rst

Feature Documentation
=====================

.. toctree::
   :maxdepth: 1

   contributor/vnfd_template_description.rst
   contributor/monitor-api.rst
   contributor/vnfd_template_parameterization.rst
   contributor/event_logging.rst
   contributor/vnffgd_template_description.rst
   contributor/tacker_conductor.rst
   contributor/tacker_vim_monitoring.rst
   contributor/policy_actions_framework.rst
   contributor/encrypt_vim_auth_with_barbican.rst

User Guide
==========

.. toctree::
   :maxdepth: 1

   user/vnfm_usage_guide.rst
   user/multisite_vim_usage_guide.rst
   user/scale_usage_guide.rst
   user/alarm_monitoring_usage_guide.rst
   user/vnffg_usage_guide.rst
   user/nsd_usage_guide.rst
   user/vnf_component_usage_guide.rst
   user/enhanced_placement_awareness_usage_guide.rst
   reference/mistral_workflows_usage_guide.rst
   reference/block_storage_usage_guide.rst

API Documentation
=================

.. toctree::
   :maxdepth: 2

   contributor/api/mano_api.rst

Contributing to Tacker
======================

.. toctree::
   :maxdepth: 1

   contributor/dev-process.rst

Developer Info
==============

.. toctree::
   :maxdepth: 1

   contributor/development.environment.rst
   contributor/api/api_layer.rst
   contributor/api/api_extensions.rst
   contributor/tacker_functional_test.rst
   contributor/dashboards.rst

Project Info
============

* **Free software:** under the `Apache license <http://www.apache.org/licenses/LICENSE-2.0>`_
* **Tacker Service:** http://git.openstack.org/cgit/openstack/tacker
* **Tacker Client Library:** http://git.openstack.org/cgit/openstack/python-tackerclient
* **Tacker Service Bugs:** http://bugs.launchpad.net/tacker
* **Client Bugs:** https://bugs.launchpad.net/python-tackerclient
* **Blueprints:** https://blueprints.launchpad.net/tacker

Indices and tables
------------------

* :ref:`search`
* :ref:`modindex`
