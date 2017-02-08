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

There are two ways to install Tacker service:

.. toctree::
   :maxdepth: 1

   install/devstack.rst
   install/manual_installation.rst

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

   devref/vnfm_usage_guide.rst
   devref/vnfd_template_description.rst
   devref/monitor-api.rst
   devref/vnfd_template_parameterization.rst
   devref/enhanced_placement_awareness_usage_guide.rst
   devref/multisite_vim_usage_guide.rst
   devref/mistral_workflows_usage_guide.rst
   devref/scale_usage_guide.rst
   devref/alarm_monitoring_usage_guide.rst
   devref/event_logging.rst
   devref/vnffgd_template_description.rst
   devref/vnffg_usage_guide.rst
   devref/nsd_usage_guide.rst
   devref/vnf_component_usage_guide.rst

API Documentation
=================

.. toctree::
   :maxdepth: 1

   devref/mano_api.rst

Contributing to Tacker
======================

.. toctree::
   :maxdepth: 1

   policies/dev-process.rst

Developer Info
==============

.. toctree::
   :maxdepth: 1

   devref/development.environment.rst
   devref/api_layer.rst
   devref/api_extensions.rst
   devref/tacker_functional_test.rst
   devref/dashboards.rst

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
