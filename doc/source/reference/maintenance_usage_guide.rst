..
      Copyright 2020 Distributed Cloud and Network (DCN)

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

================================
VNF zero impact host maintenance
================================

Tacker allows you to maintenance host with VNF zero impact. Maintenance
workflows will be performed in the ``Fenix`` service by creating a session
which can do scaling, migrating VNFs and patch hosts.


References
~~~~~~~~~~

- `Fenix   <https://fenix.readthedocs.io/en/latest/>`_.
- `Fenix Configuration Guide <https://fenix.readthedocs.io/en/latest/configuration/dependencies.html>`_.

Installation and configurations
-------------------------------

1. You need Fenix, Ceilometer and Aodh OpenStack services.

2. Modify the below configuration files:

/etc/ceilometer/event_pipeline.yaml

.. code-block:: yaml

    sinks:
      - name: event_sink
        publishers:
            - panko://
            - notifier://
            - notifier://?topic=alarm.all

/etc/ceilometer/event_definitions.yaml:

.. code-block:: yaml

    - event_type: 'maintenance.scheduled'
      traits:
        service:
          fields: payload.service
        allowed_actions:
          fields: payload.allowed_actions
        instance_ids:
          fields: payload.instance_ids
        reply_url:
          fields: payload.reply_url
        state:
          fields: payload.state
        session_id:
          fields: payload.session_id
        actions_at:
          fields: payload.actions_at
          type: datetime
        project_id:
          fields: payload.project_id
        reply_at:
          fields: payload.reply_at
          type: datetime
        metadata:
          fields: payload.metadata
    - event_type: 'maintenance.host'
      traits:
        host:
          fields: payload.host
        project_id:
          fields: payload.project_id
        session_id:
          fields: payload.session_id
        state:
          fields: payload.state


Deploying maintenance tosca template with tacker
------------------------------------------------

When template is normal
~~~~~~~~~~~~~~~~~~~~~~~

If ``Fenix`` service is enabled and maintenance event_types are defined, then
all VNF created by legacy VNFM will get ``ALL_MAINTENANCE`` resource in Stack.

.. code-block:: yaml

    resources:
      ALL_maintenance:
        properties:
          alarm_actions:
          - http://openstack-master:9890/v1.0/vnfs/e8b9bec5-541b-492c-954e-cd4af71eda1f/maintenance/0cc65f4bba9c42bfadf4aebec6ae7348/hbyhgkav
          event_type: maintenance.scheduled
        type: OS::Aodh::EventAlarm

When template has maintenance property
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If VDU in VNFD has maintenance property, then VNFM creates
``[VDU_NAME]_MAINTENANCE`` alarm resources and will be use for VNF software
modification later. This is not works yet. It will be updated.

``Sample tosca-template``:

.. code-block:: yaml

    tosca_definitions_version: tosca_simple_profile_for_nfv_1_0_0

    description: VNF TOSCA template with maintenance

    metadata:
      template_name: sample-tosca-vnfd-maintenance

    topology_template:
      node_templates:
        VDU1:
          type: tosca.nodes.nfv.VDU.Tacker
          properties:
            maintenance: True
            image: cirros-0.4.0-x86_64-disk
            capabilities:
              nfv_compute:
                properties:
                  disk_size: 1 GB
                  mem_size: 512 MB
                  num_cpus: 2

        CP1:
          type: tosca.nodes.nfv.CP.Tacker
          properties:
            management: true
            order: 0
            anti_spoofing_protection: false
          requirements:
            - virtualLink:
                node: VL1
            - virtualBinding:
                node: VDU1

        VL1:
          type: tosca.nodes.nfv.VL
          properties:
            network_name: net_mgmt
            vendor: Tacker

      policies:
        - SP1:
            type: tosca.policies.tacker.Scaling
            properties:
              increment: 1
              cooldown: 120
              min_instances: 1
              max_instances: 3
              default_instances: 2
            targets: [VDU1]


Configure maintenance constraints with config yaml
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When ``Fenix`` does maintenance, it requires some constraints for zero impact.
Like below config file, each VNF can set and update constraints.

.. code-block:: yaml

    maintenance:
      max_impacted_members: 1
      recovery_time: 60,
      mitigation_type: True,
      lead_time: 120,
      migration_type: 'MIGRATE'
