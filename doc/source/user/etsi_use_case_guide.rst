===================
v1 Tacker Use Cases
===================

.. note::

  This is a document for Tacker v1 API.
  See :doc:`/user/v2/use_case_guide` for Tacker v2 API.


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

Change External VNF Connectivity
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

VM
~~

.. toctree::
   :maxdepth: 1

   etsi_vnf_change_external_vnf_connectivity


Error Handling
^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   etsi_vnf_error_handling

.. TODO(h-asahina): add `Action Driver`
  * https://etherpad.opendev.org/p/tacker-wallaby-revise-docs

Management Driver
^^^^^^^^^^^^^^^^^

.. TODO(h-asahina): add `Overview`
  * https://etherpad.opendev.org/p/tacker-wallaby-revise-docs

Kubernetes Cluster VNF
~~~~~~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   mgmt_driver_deploy_k8s_usage_guide
   mgmt_driver_deploy_k8s_and_cnf_with_helm
   mgmt_driver_deploy_k8s_cir_usage_guide
   mgmt_driver_deploy_k8s_pv_usage_guide
   mgmt_driver_deploy_k8s_kubespary_usage_guide

Ansible Driver
~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   mgmt_driver_for_ansible_driver_usage_guide

Container Update
~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   mgmt_driver_for_container_update


VNF Package
___________

.. toctree::
   :maxdepth: 1

   sample_package
