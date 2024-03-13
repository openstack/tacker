===================
v2 Tacker Use Cases
===================


VNF
___

Deploy
^^^^^^

VM
~~

.. toctree::
   :maxdepth: 1

   vnf/deployment_with_user_data/index

Container
~~~~~~~~~

.. toctree::
   :maxdepth: 1

   cnf/deployment/index
   cnf/deployment_using_helm/index


Scale
^^^^^

VM
~~

.. toctree::
   :maxdepth: 1

   vnf/scale/index

Container
~~~~~~~~~

.. toctree::
   :maxdepth: 1

   cnf/scale/index


Heal
^^^^

VM
~~

.. toctree::
   :maxdepth: 1

   vnf/heal/index

Container
~~~~~~~~~

.. toctree::
   :maxdepth: 1

   cnf/heal/index


Update
^^^^^^

VM
~~

.. toctree::
   :maxdepth: 1

   vnf/update

Container
~~~~~~~~~

.. toctree::
   :maxdepth: 1

   cnf/update


Change External VNF Connectivity
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

VM
~~

.. toctree::
   :maxdepth: 1

   vnf/chg_ext_conn


Change Current VNF Package
^^^^^^^^^^^^^^^^^^^^^^^^^^

VM
~~

.. toctree::
   :maxdepth: 1

   vnf/chg_vnfpkg/index
   vnf/chg_vnfpkg_with_standard/index
   vnf/coordinate_api_client_script

Container
~~~~~~~~~

.. toctree::
   :maxdepth: 1

   cnf/chg_vnfpkg/index


Error Handling
^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   error_handling
   db_sync_error_handling
   placement_error_handling


Management Driver
^^^^^^^^^^^^^^^^^

Container Update
~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   cnf/update_with_mgmt_driver/index

FaultNotification AutoHealing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   fault_notification


Prometheus Plugin
^^^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   prometheus_plugin

Container
~~~~~~~~~

.. toctree::
   :maxdepth: 1

   cnf/auto_scale_pm_job/index
   cnf/auto_scale_pm_th/index
   cnf/auto_heal_fm/index
