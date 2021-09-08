================
Tacker Resources
================

Tacker mainly consists of two resources:

* Network Functions Virtualisation Orchestrator (NFVO)
* Virtualised Network Function Manager (VNFM)

*NFVO* is functional block that manages the Network Service (NS) lifecycle and
coordinates the management of NS lifecycle, VNF lifecycle (supported by the
VNFM) and NFVI resources (supported by the VIM) to ensure an optimized
allocation of the necessary resources and connectivity.

*VNFM* is functional block that is responsible for the lifecycle management of
VNF.

ETSI NFV-SOL Tacker Resources
-----------------------------

NFVO
^^^^

VNF Package
"""""""""""

.. toctree::
   :maxdepth: 1

   vnf-package

VNFM
^^^^

VNF, VNFD
"""""""""

.. toctree::
   :maxdepth: 1

   vnfd-sol001


UserData
""""""""

.. toctree::
   :maxdepth: 1

   userdata_script



Legacy Tacker Resources
-----------------------

NFVO
^^^^

VNFFG, VNFFGD
"""""""""""""

.. toctree::
   :maxdepth: 1

   ../contributor/vnffgd_template_description

.. TODO(h-asahina): add `VIM` and `NS, NSD`.
  * https://etherpad.opendev.org/p/tacker-wallaby-revise-docs


VNFM
^^^^

VNF, VNFD
"""""""""

.. toctree::
   :maxdepth: 1

   ../contributor/vnfd_template_description
   ../contributor/vnfd_template_parameterization
   vnf_component_usage_guide

Event
^^^^^

.. toctree::
   :maxdepth: 1

   ../contributor/event_logging
