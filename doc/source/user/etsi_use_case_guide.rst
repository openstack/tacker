======================
v1/v2 Tacker Use Cases
======================


VNF
___

Deploy
^^^^^^

VM
~~

.. toctree::
   :maxdepth: 1

   etsi_vnf_deployment_as_vm_with_tosca
   etsi_vnf_deployment_as_vm_with_user_data

Container
~~~~~~~~~

.. toctree::
   :maxdepth: 1

   etsi_containerized_vnf_usage_guide
   etsi_cnf_helm_v2

Scale
^^^^^

VM
~~

.. toctree::
   :maxdepth: 1

   etsi_vnf_scaling

Container
~~~~~~~~~

.. toctree::
   :maxdepth: 1

   etsi_cnf_scaling

Heal
^^^^

VM
~~

.. toctree::
   :maxdepth: 1

   etsi_vnf_healing

Container
~~~~~~~~~

.. toctree::
   :maxdepth: 1

   etsi_cnf_healing

Update
^^^^^^

VM
~~

.. toctree::
   :maxdepth: 1

   etsi_vnf_update

Container
~~~~~~~~~

.. toctree::
   :maxdepth: 1

   etsi_cnf_update

Change External VNF Connectivity
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

VM
~~

.. toctree::
   :maxdepth: 1

   etsi_vnf_change_external_vnf_connectivity

Change Current VNF Package
^^^^^^^^^^^^^^^^^^^^^^^^^^

VM
~~

.. toctree::
   :maxdepth: 1

   etsi_vnf_change_current_vnf_package
   etsi_vnf_change_current_vnf_package_with_standard_user_data
   coordinate_api_client_in_coordinatevnf_script

Container
~~~~~~~~~

.. toctree::
   :maxdepth: 1

   etsi_cnf_change_current_vnf_package

Error Handling
^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   etsi_vnf_error_handling
   db_sync_error_handling
   placement_error_handling

.. TODO(h-asahina): add `Action Driver`
  * https://etherpad.opendev.org/p/tacker-wallaby-revise-docs

Management Driver
^^^^^^^^^^^^^^^^^

.. TODO(h-asahina): add `Overview`
  * https://etherpad.opendev.org/p/tacker-wallaby-revise-docs

Kubernetes Cluster VNF (v1 API)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   mgmt_driver_deploy_k8s_usage_guide
   mgmt_driver_deploy_k8s_and_cnf_with_helm
   mgmt_driver_deploy_k8s_cir_usage_guide
   mgmt_driver_deploy_k8s_pv_usage_guide
   mgmt_driver_deploy_k8s_kubespary_usage_guide

Ansible Driver (v1 API)
~~~~~~~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   mgmt_driver_for_ansible_driver_usage_guide

Container Update (v1/v2 API)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   mgmt_driver_for_container_update

FaultNotification AutoHealing (v2 API)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   fault_notification_use_case_guide

Prometheus Plugin
^^^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   prometheus_plugin_use_case_guide

Container
~~~~~~~~~

.. toctree::
   :maxdepth: 1

   etsi_cnf_auto_scaling_pm
   etsi_cnf_auto_scaling_pm_threshold
   etsi_cnf_auto_healing_fm


VNF Package
___________

.. toctree::
   :maxdepth: 1

   sample_package
