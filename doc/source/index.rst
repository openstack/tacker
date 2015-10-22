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

============================================
Welcome to Tacker's Developer Documentation!
============================================

Tacker is OpenStack project building an Open NFV Orchestrator with in-built
general purpose VNF Manager to deploy and operate Virtual Network Functions
(VNFs) on an NFV Platform. It is based on ETSI MANO Architectural Framework
and provides full functional stack to Orchestrate VNFs end-to-end.

* **Free software:** under the `Apache license <http://www.apache.org/licenses/LICENSE-2.0>`_
* **Source:** http://git.openstack.org/cgit/openstack/tacker
* **Blueprints:** https://blueprints.launchpad.net/tacker
* **Bugs:** http://bugs.launchpad.net/tacker
* **REST Client:** http://git.openstack.org/cgit/openstack/python-tackerclient

Features
========

* VNF Catalog
* VNFM Life Cycle Management - VNF Start/Stop
* VNF Configuration Management Framework
* VNF KPI Health Monitoring Framework

Feature Documentation
=====================

.. toctree::
   :maxdepth: 1

   devref/monitor-api.rst
   devref/vnfd_template_parameterization.rst

API Documentation
=================

.. toctree::
   :maxdepth: 1

   devref/mano_api.rst

Development Process
===================

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

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
