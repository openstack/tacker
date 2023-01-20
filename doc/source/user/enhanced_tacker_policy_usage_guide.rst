==================================
Enhanced Tacker Policy Usage Guide
==================================

Overview
--------

The default Tacker API policy only supports whether the user can access the
API, but does not determine whether the users can access the resource on which
the API call operates.

Enhanced Tacker Policy enables Users to get finer-grained access control based
on user and VNF information for API resources.

This document describes how to use Enhanced Tacker Policy in Tacker.

Introduction to enhanced tacker attributes
------------------------------------------

Enhanced Tacker Policy function currently supports three enhanced attributes:
area, vendor, and tenant.

* area: Area attribute is an area-region pair. The value of this attribute is a
  string in the format of "area@region". This attribute describes the area
  where VIM or VNF is located.
* vendor: Vendor attribute is the name of the vendor. It is defined in the
  definition file of VNF package. VNF obtains this attribute from VNF package.
* tenant: Tenant attribute is the name of the tenant. Tacker Antelope version
  only supports the namespace of CNF. The tenant of VNF will be supported in
  future releases.

Enable Enhanced Tacker Policy
-----------------------------

Enhanced Tacker Policy is disabled by default in Tacker.
For it to work, user needs to find ``enhanced_tacker_policy`` in
``tacker.conf`` and change its value to ``True``. If not found, please add it
yourself.

.. code-block:: console

    $ vi /etc/tacker/tacker.conf
    ...
    [oslo_policy]
    enhanced_tacker_policy = True
    ...

Configure Enhanced Policy Rules
-------------------------------

The oslo.policy [#oslo.policy]_ supports the function to compare API attributes
to object attributes.
Based on this function, Enhanced Tacker Policy function currently supports
three enhanced tacker attributes: area, vendor, and tenant.

.. code-block:: yaml

  "get_vim" : "area:%(area)s"
  "os_nfv_orchestration_api:vnf_packages:show" : "vendor:%(vendor)s"
  "os_nfv_orchestration_api:vnf_instances:show" : "tenant:%(tenant)s"

Take the area attribute as an example, the area string before the colon is an
API attribute, namely the area of the API user. It is compared with the area of
the object (in this case, a VNF instance). More precisely, it is compared with
the area field of that object in the database. If the two values are equal,
permission is granted.

For the policy rule configuration used in this usage guide, please refer to the
`Sample policy.yaml file`_ chapter in the Appendix.

Create user with special roles
------------------------------

Users need to define special roles with the following naming rules to represent
users with access rights to corresponding resources. For example, a user with a
role of ``VENDOR_company-a`` has permission to access resources whose vendor
attribute is ``company-a``. This is because in implementation, Tacker will
convert special roles into user attributes according to the following
conversion rules for attribute comparison.

Special Roles' Naming Rules
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Enhanced Tacker Policy defines the following naming rules for special roles.
Admin user need to create special roles according to these naming rules,
otherwise Tacker will not correctly convert these special roles into user
attributes.

#.  The role name consists of three parts: prefix + "_" + [attribute
    value/special value]
#.  Supported prefixes, attribute values and special values are shown in the
    following table:

    .. list-table::
      :widths: 10 14 12 50
      :header-rows: 1

      * - Prefix
        - Attribute value
        - Special value
        - Sample
      * - AREA
        - area value
        - all@all, all@{region_value}
        - AREA_tokyo@japan, AREA_all@all, AREA_all@japan
      * - VENDOR
        - vendor value
        - all
        - VENDOR_company_a, VENDOR_all
      * - TENANT
        - tenant value
        - all
        - TENANT_default, TENANT_all

    .. note::

      As "all" is treated as a special value, the above attribute of resource
      cannot use "all" as the attribute value.

Conversion rules
~~~~~~~~~~~~~~~~

In Tacker implementation, Tacker converts these special roles into API
attributes and provide them to Tacker policy. The conversion follows the
following rules:

#.  For ordinary attribute values, they will be directly converted to user
    attribute values.

    .. list-table::
      :widths: 10 14 50
      :header-rows: 1

      * - Prefix
        - Attribute Name
        - Sample (special role -> user attribute value)
      * - AREA
        - area
        - AREA_tokyo@japan -> {"area": ["tokyo@japan"]}
      * - VENDOR
        - vendor
        - VENDOR_company-a -> {"vendor": ["company-a"]}
      * - TENANT
        - tenant value
        - TENANT_default -> {"tenant": ["default"]}

#.  For special value in Enhanced Tacker Policy, the corresponding attribute
    value of resource will be assigned to user.

    .. list-table::
      :widths: 10 14 14 50
      :header-rows: 1

      * - Prefix
        - Attribute Name
        - Special Value
        - Sample (resource attribute -> user attribute)
      * - AREA
        - area
        - all@all
        - {"area": "tokyo@japan"} -> {"area": ["tokyo@japan"]}
      * - AREA
        - area
        - all@{region_value}
        - same region value:

          .. code-block:: console

            {"area": "tokyo@japan"} -> {"area": ["tokyo@japan"]}

          different region value:

          .. code-block:: console

            any -> {"area": []}

      * - VENDOR
        - vendor
        - all
        - {"vendor": "vendor_company-a"} -> {"vendor": ["company-a"]}
      * - TENANT
        - tenant value
        - all
        - {"tenant": "default"} -> {"tenant": ["default"]}

Create users with special roles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In this user guide, user creates three end-users with admin user:

* ``user-a`` with special roles is used as the experimental group.
* ``user-b`` without special roles is used as the control group.
* ``user-manager`` with special roles and ``manager`` role as manager.

Create users
^^^^^^^^^^^^

#. Create the ``user-a`` user:

   .. code-block:: console

    $ openstack user create --project nfv --password devstack user-a
    +---------------------+----------------------------------+
    | Field               | Value                            |
    +---------------------+----------------------------------+
    | default_project_id  | 4cdc4e2efe144f87812677cfe224fffb |
    | domain_id           | default                          |
    | enabled             | True                             |
    | id                  | 57dacae03a1a41eeb0eacf481863697a |
    | name                | user-a                           |
    | options             | {}                               |
    | password_expires_at | None                             |
    +---------------------+----------------------------------+

#. Create the ``user-b`` user:

   .. code-block:: console

    $ openstack user create --project nfv --password devstack user-b
    +---------------------+----------------------------------+
    | Field               | Value                            |
    +---------------------+----------------------------------+
    | default_project_id  | 4cdc4e2efe144f87812677cfe224fffb |
    | domain_id           | default                          |
    | enabled             | True                             |
    | id                  | 3ce9d137090943e1a006392274d92f8a |
    | name                | user-b                           |
    | options             | {}                               |
    | password_expires_at | None                             |
    +---------------------+----------------------------------+

#. Create the ``user-manager`` user:

   .. code-block:: console

    $ openstack user create --project nfv --password devstack user-manager
    +---------------------+----------------------------------+
    | Field               | Value                            |
    +---------------------+----------------------------------+
    | default_project_id  | 4cdc4e2efe144f87812677cfe224fffb |
    | domain_id           | default                          |
    | enabled             | True                             |
    | id                  | 53f085076d9d4324bbe8498d92aa5292 |
    | name                | user-manager                     |
    | options             | {}                               |
    | password_expires_at | None                             |
    +---------------------+----------------------------------+

Create roles
^^^^^^^^^^^^

#. Create the ``AREA_tokyo@japan`` role:

   .. code-block:: console

    $ openstack role create AREA_tokyo@japan
    +-------------+----------------------------------+
    | Field       | Value                            |
    +-------------+----------------------------------+
    | description | None                             |
    | domain_id   | None                             |
    | id          | b059c62190b34877a9e6f649108161e7 |
    | name        | AREA_tokyo@japan                 |
    | options     | {}                               |
    +-------------+----------------------------------+

#. Create the ``AREA_all@all`` role:

   .. code-block:: console

    $ openstack role create AREA_all@all
    +-------------+----------------------------------+
    | Field       | Value                            |
    +-------------+----------------------------------+
    | description | None                             |
    | domain_id   | None                             |
    | id          | b7c1f766a0884064aac130807844d429 |
    | name        | AREA_all@all                     |
    | options     | {}                               |
    +-------------+----------------------------------+

#. Create the ``VENDOR_company-a`` role:

   .. code-block:: console

    $ openstack role create VENDOR_company-a
    +-------------+----------------------------------+
    | Field       | Value                            |
    +-------------+----------------------------------+
    | description | None                             |
    | domain_id   | None                             |
    | id          | 9bdacbbb96c14a849e4e0e86cd627845 |
    | name        | VENDOR_company-a                 |
    | options     | {}                               |
    +-------------+----------------------------------+

#. Create the ``VENDOR_all`` role:

   .. code-block:: console

    $ openstack role create VENDOR_all
    +-------------+----------------------------------+
    | Field       | Value                            |
    +-------------+----------------------------------+
    | description | None                             |
    | domain_id   | None                             |
    | id          | 28f0bb8a07bb44c3973e2922c8380ef2 |
    | name        | VENDOR_all                       |
    | options     | {}                               |
    +-------------+----------------------------------+

#. Create the ``TENANT_curry`` role:

   .. code-block:: console

    $ openstack role create TENANT_curry
    +-------------+----------------------------------+
    | Field       | Value                            |
    +-------------+----------------------------------+
    | description | None                             |
    | domain_id   | None                             |
    | id          | cb98edb048ad49399701d4397708f397 |
    | name        | TENANT_curry                     |
    | options     | {}                               |
    +-------------+----------------------------------+

#. Create the ``TENANT_all`` role:

   .. code-block:: console

    $ openstack role create TENANT_all
    +-------------+----------------------------------+
    | Field       | Value                            |
    +-------------+----------------------------------+
    | description | None                             |
    | domain_id   | None                             |
    | id          | b2ab9d7eec8c4b978417aff45206a7e0 |
    | name        | TENANT_all                       |
    | options     | {}                               |
    +-------------+----------------------------------+

#. Create the ``manager`` role:

   .. code-block:: console

    $ openstack role create manager
    +-------------+----------------------------------+
    | Field       | Value                            |
    +-------------+----------------------------------+
    | description | None                             |
    | domain_id   | None                             |
    | id          | d4bc947fca0f41368ade7173a9f0f9cb |
    | name        | manager                          |
    | options     | {}                               |
    +-------------+----------------------------------+

Assign roles to user-project pairs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. Assign ``AREA_tokyo@japan``, ``VENDOR_company-a`` and ``TENANT_curry``
   to ``user-a``:

   .. code-block:: console

    $ openstack role add --user user-a --project nfv AREA_tokyo@japan
    $ openstack role add --user user-a --project nfv VENDOR_company-a
    $ openstack role add --user user-a --project nfv TENANT_curry

   Verify the role assignment of ``user-a``:

   .. code-block:: console

    $ openstack role assignment list --user user-a --project nfv --names
    +------------------+----------------+-------+-------------+--------+--------+-----------+
    | Role             | User           | Group | Project     | Domain | System | Inherited |
    +------------------+----------------+-------+-------------+--------+--------+-----------+
    | VENDOR_company-a | user-a@Default |       | nfv@Default |        |        | False     |
    | AREA_tokyo@japan | user-a@Default |       | nfv@Default |        |        | False     |
    | TENANT_curry     | user-a@Default |       | nfv@Default |        |        | False     |
    +------------------+----------------+-------+-------------+--------+--------+-----------+

#. Assign reader to ``user-b``:

   .. code-block:: console

    $ openstack role add --user user-b --project nfv reader

   Verify the role assignment of ``user-b``:

   .. code-block:: console

    $ openstack role assignment list --user user-b --project nfv --names
    +--------+----------------+-------+-------------+--------+--------+-----------+
    | Role   | User           | Group | Project     | Domain | System | Inherited |
    +--------+----------------+-------+-------------+--------+--------+-----------+
    | reader | user-b@Default |       | nfv@Default |        |        | False     |
    +--------+----------------+-------+-------------+--------+--------+-----------+

#. Assign ``AREA_all@all``, ``VENDOR_all`` and ``TENANT_all`` to
   ``user-manager``:

   .. code-block:: console

    $ openstack role add --user user-manager --project nfv AREA_all@all
    $ openstack role add --user user-manager --project nfv VENDOR_all
    $ openstack role add --user user-manager --project nfv TENANT_all
    $ openstack role add --user user-manager --project nfv manager

   Verify the role assignment of ``user-manager``:

   .. code-block:: console

    $ openstack role assignment list --user user-manager --project nfv --names
    +---------------+----------------------+-------+-------------+--------+--------+-----------+
    | Role          | User                 | Group | Project     | Domain | System | Inherited |
    +---------------+----------------------+-------+-------------+--------+--------+-----------+
    | VENDOR_all    | user-manager@Default |       | nfv@Default |        |        | False     |
    | TENANT_all    | user-manager@Default |       | nfv@Default |        |        | False     |
    | AREA_all@all  | user-manager@Default |       | nfv@Default |        |        | False     |
    | manager       | user-manager@Default |       | nfv@Default |        |        | False     |
    +---------------+----------------------+-------+-------------+--------+--------+-----------+

Create resources with enhanced tacker attributes
------------------------------------------------

This section describes how to create resources with enhanced tacker
attributes, using examples.

Register vim with area attribute
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When registering a vim, users can specify area attribute for the vim. This is
achieved by putting the area attribute into the extra field of the vim
configuration file. Please refer to VIM Management [#VIM_Management]_ for how
to register a vim.

.. warning::
    It is highly recommended that users who performs the VIM registration is
    isolated from users who call VNF LCM APIs. Otherwise, users can ignore
    area attribute if VIM by overwriting.

#. Register an OpenStack VIM with area attribute ``tokyo@japan``.

   Sample ``vim_config.yaml`` file for OpenStack VIM:

   .. code-block:: yaml

    auth_url: 'http://192.168.10.115/identity/v3'
    username: 'nfv_user'
    password: 'devstack'
    project_name: 'nfv'
    project_domain_name: 'default'
    user_domain_name: 'default'
    cert_verify: 'True'
    extra:
        area: tokyo@japan

   Register OpenStack VIM:

   .. code-block:: console

    $ openstack vim register --config-file ./vim_config.yaml \
        --description 'openstack vim in nfv' \
        openstack-tokyo@japan
    +----------------+------------------------------------------------------+
    | Field          | Value                                                |
    +----------------+------------------------------------------------------+
    | auth_cred      | {                                                    |
    |                |     "username": "nfv_user",                          |
    |                |     "user_domain_name": "default",                   |
    |                |     "cert_verify": "True",                           |
    |                |     "project_id": null,                              |
    |                |     "project_name": "nfv",                           |
    |                |     "project_domain_name": "default",                |
    |                |     "auth_url": "http://192.168.10.115/identity/v3", |
    |                |     "key_type": "barbican_key",                      |
    |                |     "secret_uuid": "***",                            |
    |                |     "password": "***"                                |
    |                | }                                                    |
    | auth_url       | http://192.168.10.115/identity/v3                    |
    | created_at     | 2023-02-14 07:05:26.234729                           |
    | description    | openstack vim in nfv                                 |
    | extra          | area=tokyo@japan                                     |
    | id             | 95f633de-d2d1-4d90-90f7-0f3839369ff2                 |
    | is_default     | False                                                |
    | name           | openstack-tokyo@japan                                |
    | placement_attr | {                                                    |
    |                |     "regions": [                                     |
    |                |         "RegionOne"                                  |
    |                |     ]                                                |
    |                | }                                                    |
    | project_id     | 4cdc4e2efe144f87812677cfe224fffb                     |
    | status         | PENDING                                              |
    | type           | openstack                                            |
    | updated_at     | None                                                 |
    | vim_project    | {                                                    |
    |                |     "name": "nfv",                                   |
    |                |     "project_domain_name": "default"                 |
    |                | }                                                    |
    +----------------+------------------------------------------------------+

#. Register a OpenStack VIM with area attribute ``osaka@japan``.

   Sample ``vim_config.yaml`` file for OpenStack VIM:

   .. code-block:: yaml

    auth_url: 'http://192.168.10.115/identity/v3'
    username: 'nfv_user'
    password: 'devstack'
    project_name: 'nfv'
    project_domain_name: 'default'
    user_domain_name: 'default'
    cert_verify: 'True'
    extra:
        area: osaka@japan

   Register OpenStack VIM:

   .. code-block:: console

    $ openstack vim register --config-file ./vim_config.yaml \
        --description 'openstack vim in nfv' \
        openstack-osaka@japan
    +----------------+------------------------------------------------------+
    | Field          | Value                                                |
    +----------------+------------------------------------------------------+
    | auth_cred      | {                                                    |
    |                |     "username": "nfv_user",                          |
    |                |     "user_domain_name": "default",                   |
    |                |     "cert_verify": "True",                           |
    |                |     "project_id": null,                              |
    |                |     "project_name": "nfv",                           |
    |                |     "project_domain_name": "default",                |
    |                |     "auth_url": "http://192.168.10.115/identity/v3", |
    |                |     "key_type": "barbican_key",                      |
    |                |     "secret_uuid": "***",                            |
    |                |     "password": "***"                                |
    |                | }                                                    |
    | auth_url       | http://192.168.10.115/identity/v3                    |
    | created_at     | 2023-02-14 07:07:36.934208                           |
    | description    | openstack vim in nfv                                 |
    | extra          | area=osaka@japan                                     |
    | id             | cd63517f-95c2-4088-ab67-36420ab87ed7                 |
    | is_default     | False                                                |
    | name           | openstack-osaka@japan                                |
    | placement_attr | {                                                    |
    |                |     "regions": [                                     |
    |                |         "RegionOne"                                  |
    |                |     ]                                                |
    |                | }                                                    |
    | project_id     | 4cdc4e2efe144f87812677cfe224fffb                     |
    | status         | PENDING                                              |
    | type           | openstack                                            |
    | updated_at     | None                                                 |
    | vim_project    | {                                                    |
    |                |     "name": "nfv",                                   |
    |                |     "project_domain_name": "default"                 |
    |                | }                                                    |
    +----------------+------------------------------------------------------+

#. Register a Kubernetes VIM with area attribute ``tokyo@japan``.

   Sample ``vim_config_k8s.yaml`` file for Kubernetes VIM:

   .. code-block:: yaml

    auth_url: "https://kubernetes.default.svc:6443"
    bearer_token: "eyJhbGciOiJSUzI1NiIsImtpZCI6IjlrcFJlLVBRREoxZDRHVVRFS1g4eHBFQzFqRWpqOWNhSmRkbDVtY0tqWW8ifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJrdWJlLXN5c3RlbSIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VjcmV0Lm5hbWUiOiJhZG1pbi10b2tlbi1rOHN2aW0iLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoiYWRtaW4iLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC51aWQiOiIwM2M3ODRjNi0yNjhkLTQ5ZTgtYjU1Yi0zNDJhMmFiMjM1ZDUiLCJzdWIiOiJzeXN0ZW06c2VydmljZWFjY291bnQ6a3ViZS1zeXN0ZW06YWRtaW4ifQ.KgqK6nBOnJaJ6uxmbLilYjenUbEwVvJ3-Ynbulw2GjGgMfbhO4lXR57nVdA9LkM17NyiUnP01t7b6BzzUPELQA03q5ufGkZns9d7xzlmb6SAKzTXh2rdh3skUDtv4dMHTqf7-e6K9VWtQPRo9qfCgRR_nrU4ED9ycjE707kcopbrOTk_EEZ-roPBTWZl5OgFQrTl5y-xVPcHNqF2vN-l6t8M_3g6PZV6yQl0ul4iBrfGpnMQyvJcgUBmFe2o1L3ey4VXC9aR0FLz--vi9K7TntBrm5pipAJIrLdDImws00P5hylyAavY8OACInyNWPkHeVK0D49koV9J1J5kR_paxQ"
    project_name: "default"
    ssl_ca_cert: "-----BEGIN CERTIFICATE-----
    MIIC/jCCAeagAwIBAgIBADANBgkqhkiG9w0BAQsFADAVMRMwEQYDVQQDEwprdWJl
    cm5ldGVzMB4XDTIyMTIwNTA1MzIwOFoXDTMyMTIwMjA1MzIwOFowFTETMBEGA1UE
    AxMKa3ViZXJuZXRlczCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAMHS
    8d5g+5Qxhw5ViKwQo8kAWf/wxmfrT5sPQZfCfb/lnxt2kdiUkbhPlM2f4SLSz0CF
    3QM+6rFCP3ajOKyVF4/Gom/qwNseGrxKW3PxzWqA4PBgXk4wiv/VVXiAm0TS6fMd
    GnuVqebV7Q8lue6YnuK1ttDsYSpHiEaiWW1g9eBV4/BRHUFHKRHO4b1u2c+s3MSV
    NpPGgyVEqwAk76kDNJGcrihP7Ze3TRWHY52VCjsZZ4x4zQrAtsCYL9to6PcOxz7z
    ZFL4SKOlOXdQieIZ47DTHWKlB6gshxQiWd74AEzzVH3jMSRPnSTipcFzwL9z7AY6
    r1SzLb9TngxrjiNdndcCAwEAAaNZMFcwDgYDVR0PAQH/BAQDAgKkMA8GA1UdEwEB
    /wQFMAMBAf8wHQYDVR0OBBYEFAHIWsqm7ffo4EF4dDbUWFHQAZjLMBUGA1UdEQQO
    MAyCCmt1YmVybmV0ZXMwDQYJKoZIhvcNAQELBQADggEBAEQuTS5F6g/XRnjF9C1v
    umi1ZphbOUVcrAifRMVFV1fLqa9kgKH/mgl0JN04CE2fCErJYxBmlGlCJQcihlkk
    sZu6/dQ1hgI4pS891kCpSu5RExDNj5fm7X3s/OuxqIBsOr2CayEhWyKkqXyT9CoR
    jsfyfq/WQYxbhq92l7sB+tWI0/sVHWVaouY7QzXdP6d6LkC58f7t5d0p46X3sECK
    jPUFktAZb2axK4ipHRYxYzB7n7RB6K+nNsaaZOhWMxCa4835yleuRp6Caq9TnV75
    YW8MCUN6YNEQ1PYpGMuguAkAsS62QeL7/1VCUzYo/Rxu7l5sErjcKtq6bWWJ3eM6
    Yx4=
    -----END CERTIFICATE-----"
    type: "kubernetes"
    extra:
      use_helm: true
      area: tokyo@japan

   Register Kubernetes VIM:

   .. code-block:: console

    $ openstack vim register --config-file ./vim_k8s_config.yaml \
        --description 'kubernetes vim in nfv' \
        kubernetes-tokyo@japan --fit-width
    +----------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | Field          | Value                                                                                                                                                          |
    +----------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | auth_cred      | {                                                                                                                                                              |
    |                |     "bearer_token": "***",                                                                                                                                     |
    |                |     "ssl_ca_cert": "b'gAAAAABj6zRs0_iM8WzO3BPSdafLsnunr8jA1Kx-9V3ITS-m_2W7_Z76hmH3zXHSOn8zmwwUbKoWBl74QTHOne-                                                  |
    |                | z_Uwuc5tJuaKaEgfOUX8UkifhVhA2-V6zZyQ5nFoLVLmzwN1oSUmFaT-yli9Noel0oi4xK03WxvnOj01F_LcGFXnJahSg74FYCoRRQpSng9IBYy_jCIeLCPtoeWpxx1Yske-2nyOCXmcxnEgbOw79s-8qL07iu |
    |                | Ln2nYBS7buGTZ64nmCPNiUWsFeccOCX8rdoTSOiKaeSVFQYlfos5eUA8V-6RKJECEtmbjUWyoc1084uTukS_0-o--rLsnOklAfkDuArC2l_w62iMxLGmsQQO3dD5C9nImbdKkR0xRRTayRiCKDFqCua9Ny2UIy |
    |                | WdsNYziX1oxhYeeguHkL1b9hIzlU3pStuEkcqhmX1R9-E4Heh0h4uJb_2wc_R540-Wq0x7faKhPbWx4kuyr4S1S4KplDuyWCpQEWTlZ957-S5n50pnsTRTrjPi25VvYtQ3c7yyZjQaNIf0bJ9eXVbG2OhnZOWC |
    |                | hOX-_B_CsqP27_zdQ5etxj-                                                                                                                                        |
    |                | Dct9VGHpD29Sra_bLUw3_EUHxvB4J-Rb0FyinKzOuLJSB52kPZ5Ay2k8_jwEQyrXK6ZqJYAP24XtQFrFl7FMCiYoep_6cYrB2WX8nCwQW4BqLDV4astJEGHRSVwEiJklF3BBNCeuJ-MhMmtm-              |
    |                | hulnqw7tSHYYUHKzKcU30_XZKHdp5dqtsmGJvbuvfwbbKX0fjHasi8PQrI_7982OLF55JkXsmdu-vemoJe8RQZC2KX9nZI8qOVTqmmqkAo3GupcCgLMPItaLjogeEkLmqy30L7WOrXU9em3oq7828gufPS6JmG |
    |                | FpqridqJf8onbljrayND2050-XmgzaEOLtzah9YZaIo4_97Ki4QyCtVk2uauP0_po3jcGnU1qklOZyqdRAkZ9sWTiWUdfmmxjpE_JHgwu8VeFJFVB1y5is7O7Ww4YNvVCGjZYPzQVzomssjmWgtAqzu_biDrv0 |
    |                | JvAz4OjV3VgRUhSW_VDIUmCnlx6zWWoPckOVuGAIAX0Q93afUqdOPsLB9QU0J4D1eTTQcjCOMWROMSDvsi11KN6ejmp7fiki5KRQX8hZGmo2d71OmkPhap8KSW2hcV2EfZlLOT0i5RQZNpfuc3BWUnKgeSW1OM |
    |                | FssJLiDScFry-7VvMjQCIVYWH7amMubSNGVuPvN5dFhUk6CukjAmW82VZ9pvz1XymohS48FSYBfRiTgO6m4BMkxhVb1sMOMCBSysi8NIc75YHh4vwvTkmt5pu6wZcIisdGgwTgkOoYezmBex2agQXJ2vCiO-   |
    |                | bLAISkCyl-Bs0dF-TI3HEVv0twRXBZsSJiaF8lmk_lOlqP5rFLwk37JCvFC-MMRWHl9pBcvr-FLWyUGVVL1WDaWnW6o3cEz0iwRw5wFmy7kqZw_3FAj0qguCq6UQ-                                  |
    |                | NDBaePMyv9vJJJrXVInsJA6J17b9iA97UqNlzydb07Ag4TBgSipsC1NZwbMJR87D'",                                                                                            |
    |                |     "auth_url": "https://kubernetes.default.svc:6443",                                                                                                         |
    |                |     "username": "None",                                                                                                                                        |
    |                |     "key_type": "barbican_key",                                                                                                                                |
    |                |     "secret_uuid": "***"                                                                                                                                       |
    |                | }                                                                                                                                                              |
    | auth_url       | https://kubernetes.default.svc:6443                                                                                                                            |
    | created_at     | 2023-02-14 07:12:45.027780                                                                                                                                     |
    | description    | kubernetes vim in nfv                                                                                                                                          |
    | extra          | area=tokyo@japan, use_helm=True                                                                                                                                |
    | id             | 705f23fc-054f-46c4-bcfe-922d11d85b27                                                                                                                           |
    | is_default     | False                                                                                                                                                          |
    | name           | kubernetes-tokyo@japan                                                                                                                                         |
    | placement_attr | {                                                                                                                                                              |
    |                |     "regions": [                                                                                                                                               |
    |                |         "default",                                                                                                                                             |
    |                |         "kube-node-lease",                                                                                                                                     |
    |                |         "kube-public",                                                                                                                                         |
    |                |         "kube-system",                                                                                                                                         |
    |                |         "syg"                                                                                                                                                  |
    |                |     ]                                                                                                                                                          |
    |                | }                                                                                                                                                              |
    | project_id     | 4cdc4e2efe144f87812677cfe224fffb                                                                                                                               |
    | status         | PENDING                                                                                                                                                        |
    | type           | kubernetes                                                                                                                                                     |
    | updated_at     | None                                                                                                                                                           |
    | vim_project    | {                                                                                                                                                              |
    |                |     "name": "default"                                                                                                                                          |
    |                | }                                                                                                                                                              |
    +----------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------+

Create VNF package with vendor attribute
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The vendor attribute of the VNF package resource comes from the provider field
defined in ``Definitions/vnfd_top.yaml`` of the VNF package. To create a VNF
package with a specified vendor attribute, users need to modify the provider
attribute to vendor. Please refer to VNF Package [#VNF_Package]_ for how to
make zip file and create VNF packages. This chapter only gives a sample of
configuration files that need to be modified in VNF package.

#. Set the provider in ``Definitions/vnfd_top.yaml`` to ``company-a``.

   .. code-block:: yaml

    tosca_definitions_version: tosca_simple_yaml_1_2

    description: Sample VNF

    imports:
      - etsi_nfv_sol001_common_types.yaml
      - etsi_nfv_sol001_vnfd_types.yaml
      - sample_vnfd_types.yaml
      - sample_vnfd_df_simple.yaml

    topology_template:
      inputs:
        selected_flavour:
          type: string
          description: VNF deployment flavour selected by the consumer. It is provided in the API

      node_templates:
        VNF:
          type: company.provider.VNF
          properties:
            flavour_id: { get_input: selected_flavour }
            descriptor_id: c1bb0ce7-ebca-4fa7-95ed-4840d70a1175
            provider: company-a
            product_name: Sample VNF
            software_version: "1.0"
            descriptor_version: "1.0"
            vnfm_info:
              - Tacker
          requirements:
            #- virtual_link_external # mapped in lower-level templates
            #- virtual_link_internal # mapped in lower-level templates

#. Set the provider in ``Definitions/vnfd_types.yaml`` to ``company-a``.

   .. code-block:: yaml

    tosca_definitions_version: tosca_simple_yaml_1_2

    description: VNF type definition

    imports:
      - etsi_nfv_sol001_common_types.yaml
      - etsi_nfv_sol001_vnfd_types.yaml

    node_types:
      company.provider.VNF:
        derived_from: tosca.nodes.nfv.VNF
        properties:
          ...
          provider:
            type: string
            constraints: [valid_values: ["company-a"]]
            default: "company-a"
          ...

Create & Instantiate VNF with vendor, area and tenant attributes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create VNF with vendor attribute
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The vendor attribute of the VNF comes from the provider attribute of the VNF
package. Therefore, users only need to use the VNF package with the specified
provider attribute to create a VNF with the specified vendor attribute.

The following is an example of creating a VNF with the specified vendor
attribute.

Create a VNF with vnfd_id:

.. code-block:: console

    $ openstack vnflcm create <vnfd_id>

Instantiate VNF on VIM with area attributes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The area attribute of the VNF comes from the used vim. In other
words, you need to specify a VIM in the area where you want to
instantiate a VNF.

For VNF LCM API version 1, please refer to [#VNF_Lifecycle_Management]_ to
instantiate VNF. Below are two samples of <param-file>.

#. If <param-file> contains the ``vimConnectionInfo`` parameter, the area
   attribute comes from vim in it.

   .. code-block:: json

    {
        "flavourId": "simple",
        "extVirtualLinks": [
            {
                "id": "net0",
                "resourceId": "1d868d02-ecd4-4402-8e6b-54e77ebdcc28",
                "extCps": [
                    {
                        "cpdId": "CP1",
                        "cpConfig": [
                            {
                                "cpProtocolData": [
                                    {
                                        "layerProtocol": "IP_OVER_ETHERNET",
                                        "ipOverEthernet": {
                                            "ipAddresses": [
                                                {
                                                    "type": "IPV4",
                                                    "numDynamicAddresses": 1,
                                                    "subnetId": "109f5049-b51e-409a-9a99-d740ba5f3acb"
                                                }
                                            ]
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ],
        "vimConnectionInfo": [
            {
                "id": "e24f9796-a8e9-4cb0-85ce-5920dcddafa1",
                "vimId": "991a1e07-e8a2-4e1b-b77d-3937177a5b7f",
                "vimType": "ETSINFV.OPENSTACK_KEYSTONE.v_2"
            }
        ],
        "additionalParams": {
            "lcm-operation-user-data": "./UserData/lcm_user_data.py",
            "lcm-operation-user-data-class": "SampleUserData"
        }
    }


#. If <param-file> doesn't contains the ``vimConnectionInfo`` parameter, the
   default vim is used and area attribute comes from it.

   .. code-block:: json

    {
        "flavourId": "simple"
    }

For VNF LCM API version 2, please refer to [#VNF_Lifecycle_Management]_ to
instantiate VNF. Below are two samples of <param-file>.

#. If the vim in the ``vimConnectionInfo`` parameter of <param-file> is an
   existing vim in the DB, the vendor attribute of the instantiated VNF
   comes from this vim.

   .. code-block:: json

    {
        "extManagedVirtualLinks": [
            {
                "id": "7a6fe192-c34b-4029-937d-f1a2e7a00f5a",
                "resourceId": "11f8a056-0495-4ca6-8de9-94402604663f",
                "vnfVirtualLinkDescId": "internalVL1"
            }
        ],
        "extVirtualLinks": [
            {
                "extCps": [
                    {
                        "cpConfig": {
                            "VDU1_CP1_1": {
                                "cpProtocolData": [
                                    {
                                        "ipOverEthernet": {
                                            "ipAddresses": [
                                                {
                                                    "numDynamicAddresses": 1,
                                                    "type": "IPV4"
                                                }
                                            ]
                                        },
                                        "layerProtocol": "IP_OVER_ETHERNET"
                                    }
                                ]
                            }
                        },
                        "cpdId": "VDU1_CP1"
                    },
                    {
                        "cpConfig": {
                            "VDU2_CP1_1": {
                                "cpProtocolData": [
                                    {
                                        "ipOverEthernet": {
                                            "ipAddresses": [
                                                {
                                                    "fixedAddresses": [
                                                        "10.10.0.101"
                                                    ],
                                                    "type": "IPV4"
                                                }
                                            ]
                                        },
                                        "layerProtocol": "IP_OVER_ETHERNET"
                                    }
                                ]
                            }
                        },
                        "cpdId": "VDU2_CP1"
                    }
                ],
                "id": "b0b2f836-a275-4374-834e-ed336a563b1e",
                "resourceId": "1948231e-bbf0-4ff9-a692-40f8d6d5c90d"
            },
            {
                "extCps": [
                    {
                        "cpConfig": {
                            "VDU1_CP2_1": {
                                "cpProtocolData": [
                                    {
                                        "ipOverEthernet": {
                                            "ipAddresses": [
                                                {
                                                    "numDynamicAddresses": 1,
                                                    "subnetId": "1d4877ea-b810-4093-95de-bee62b2363f1",
                                                    "type": "IPV4"
                                                }
                                            ]
                                        },
                                        "layerProtocol": "IP_OVER_ETHERNET"
                                    }
                                ]
                            }
                        },
                        "cpdId": "VDU1_CP2"
                    },
                    {
                        "cpConfig": {
                            "VDU2_CP2_1": {
                                "cpProtocolData": [
                                    {
                                        "ipOverEthernet": {
                                            "ipAddresses": [
                                                {
                                                    "fixedAddresses": [
                                                        "10.10.1.101"
                                                    ],
                                                    "subnetId": "1d4877ea-b810-4093-95de-bee62b2363f1",
                                                    "type": "IPV4"
                                                }
                                            ]
                                        },
                                        "layerProtocol": "IP_OVER_ETHERNET"
                                    }
                                ]
                            }
                        },
                        "cpdId": "VDU2_CP2"
                    }
                ],
                "id": "6766a8d4-cad1-43f1-b0cb-ce0ef9267661",
                "resourceId": "5af7e28a-e744-4b4f-a1a4-c7d0f7d93cd7"
            }
        ],
        "flavourId": "simple",
        "instantiationLevelId": "instantiation_level_1",
        "vimConnectionInfo": {
            "vim1": {
                "id": "725f625e-f6b7-4bcd-b1b7-7184039fde45"
                "vimId": "03e608b2-e7d4-44fa-bd84-74fb24be3ed5",
                "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3"
            }
        }
    }

#. If the vim in the ``vimConnectionInfo`` parameter of <param-file> is not
   existed in the DB, the vendor attribute of the instantiated VNF comes from
   this vim. Users need to specify the area attribute in the
   ``vimConnectionInfo`` parameter.

   .. code-block:: json

    {
        "extManagedVirtualLinks": [
            {
                "id": "7a6fe192-c34b-4029-937d-f1a2e7a00f5a",
                "resourceId": "11f8a056-0495-4ca6-8de9-94402604663f",
                "vnfVirtualLinkDescId": "internalVL1"
            }
        ],
        "extVirtualLinks": [
            {
                "extCps": [
                    {
                        "cpConfig": {
                            "VDU1_CP1_1": {
                                "cpProtocolData": [
                                    {
                                        "ipOverEthernet": {
                                            "ipAddresses": [
                                                {
                                                    "numDynamicAddresses": 1,
                                                    "type": "IPV4"
                                                }
                                            ]
                                        },
                                        "layerProtocol": "IP_OVER_ETHERNET"
                                    }
                                ]
                            }
                        },
                        "cpdId": "VDU1_CP1"
                    },
                    {
                        "cpConfig": {
                            "VDU2_CP1_1": {
                                "cpProtocolData": [
                                    {
                                        "ipOverEthernet": {
                                            "ipAddresses": [
                                                {
                                                    "fixedAddresses": [
                                                        "10.10.0.101"
                                                    ],
                                                    "type": "IPV4"
                                                }
                                            ]
                                        },
                                        "layerProtocol": "IP_OVER_ETHERNET"
                                    }
                                ]
                            }
                        },
                        "cpdId": "VDU2_CP1"
                    }
                ],
                "id": "b0b2f836-a275-4374-834e-ed336a563b1e",
                "resourceId": "1948231e-bbf0-4ff9-a692-40f8d6d5c90d"
            },
            {
                "extCps": [
                    {
                        "cpConfig": {
                            "VDU1_CP2_1": {
                                "cpProtocolData": [
                                    {
                                        "ipOverEthernet": {
                                            "ipAddresses": [
                                                {
                                                    "numDynamicAddresses": 1,
                                                    "subnetId": "1d4877ea-b810-4093-95de-bee62b2363f1",
                                                    "type": "IPV4"
                                                }
                                            ]
                                        },
                                        "layerProtocol": "IP_OVER_ETHERNET"
                                    }
                                ]
                            }
                        },
                        "cpdId": "VDU1_CP2"
                    },
                    {
                        "cpConfig": {
                            "VDU2_CP2_1": {
                                "cpProtocolData": [
                                    {
                                        "ipOverEthernet": {
                                            "ipAddresses": [
                                                {
                                                    "fixedAddresses": [
                                                        "10.10.1.101"
                                                    ],
                                                    "subnetId": "1d4877ea-b810-4093-95de-bee62b2363f1",
                                                    "type": "IPV4"
                                                }
                                            ]
                                        },
                                        "layerProtocol": "IP_OVER_ETHERNET"
                                    }
                                ]
                            }
                        },
                        "cpdId": "VDU2_CP2"
                    }
                ],
                "id": "6766a8d4-cad1-43f1-b0cb-ce0ef9267661",
                "resourceId": "5af7e28a-e744-4b4f-a1a4-c7d0f7d93cd7"
            }
        ],
        "flavourId": "simple",
        "instantiationLevelId": "instantiation_level_1",
        "vimConnectionInfo": {
            "vim1": {
                "accessInfo": {
                    "password": "devstack",
                    "project": "nfv",
                    "projectDomain": "Default",
                    "region": "RegionOne",
                    "userDomain": "Default",
                    "username": "nfv_user"
                },
                "interfaceInfo": {
                    "endpoint": "http://localhost/identity/v3"
                },
                "vimId": "03e608b2-e7d4-44fa-bd84-74fb24be3ed5",
                "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
                "extra": {"area": "tokyo@japan"}
            }
        }
    }

Instantiate CNF with tenant attribute
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In Tacker Antelope verison, only CNF has the tenant attribute. When
instantiating CNF, the tenant attribute of CNF is specified by the namespace in
the additionalParams field of <param-file>.

.. code-block:: json

    {
        "flavourId": "simple",
        "vimConnectionInfo": [
            {
                "id": "b1bb0ce7-ebca-4fa7-95ed-4840d70a1177",
                "vimId": "725f625e-f6b7-4bcd-b1b7-7184039fde45",
                "vimType": "kubernetes"
            }
        ],
        "additionalParams": {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/deployment.yaml",
                "Files/kubernetes/namespace.yaml"
            ],
            "namespace": "curry"
        }
    }

Usage of APIs supporting Enhanced Tacker Policy
-----------------------------------------------

This section takes the VIM Management API as an example to introduce the API
calls that support Enhanced Tacker Policy. You can find a list of APIs that
support Enhanced Tacker Policy and the enhanced tacker attributes supported by
each API in `Tacker APIs that support Enhanced Tacker Policy`_.

GET individual resources
~~~~~~~~~~~~~~~~~~~~~~~~

Users with special roles have permission to access corresponding resources. For
example, ``user-a`` who has the role of ``AREA_tokyo@japan`` has permission
to access the VIM with area attribute ``tokyo@japan``. ``user-b`` who does
not have the role of ``AREA_tokyo@japan`` does not have permission to
access the VIM with area attribute ``tokyo@japan``. Here take Show VIM as
an example.

``user-a`` shows VIM whose area attribute is ``tokyo@japan``, and it succeeds.

.. code-block:: console

    $ openstack vim show 95f633de-d2d1-4d90-90f7-0f3839369ff2
    +----------------+------------------------------------------------------+
    | Field          | Value                                                |
    +----------------+------------------------------------------------------+
    | auth_cred      | {                                                    |
    |                |     "username": "nfv_user",                          |
    |                |     "user_domain_name": "default",                   |
    |                |     "cert_verify": "True",                           |
    |                |     "project_id": null,                              |
    |                |     "project_name": "nfv",                           |
    |                |     "project_domain_name": "default",                |
    |                |     "auth_url": "http://192.168.10.115/identity/v3", |
    |                |     "key_type": "barbican_key",                      |
    |                |     "secret_uuid": "***",                            |
    |                |     "password": "***"                                |
    |                | }                                                    |
    | auth_url       | http://192.168.10.115/identity/v3                    |
    | created_at     | 2023-02-14 07:05:26                                  |
    | description    | openstack vim in nfv                                 |
    | extra          | area=tokyo@japan                                     |
    | id             | 95f633de-d2d1-4d90-90f7-0f3839369ff2                 |
    | is_default     | False                                                |
    | name           | openstack-tokyo@japan                                |
    | placement_attr | {                                                    |
    |                |     "regions": [                                     |
    |                |         "RegionOne"                                  |
    |                |     ]                                                |
    |                | }                                                    |
    | project_id     | 4cdc4e2efe144f87812677cfe224fffb                     |
    | status         | REACHABLE                                            |
    | type           | openstack                                            |
    | updated_at     | 2023-02-14 07:05:28                                  |
    | vim_project    | {                                                    |
    |                |     "name": "nfv",                                   |
    |                |     "project_domain_name": "default"                 |
    |                | }                                                    |
    +----------------+------------------------------------------------------+

``user-b`` shows VIM whose area attribute is ``tokyo@japan``, and it fails.

.. code-block:: console

    $ openstack vim show 95f633de-d2d1-4d90-90f7-0f3839369ff2
    The request you have made requires authentication. (HTTP 401) (Request-ID: req-4875a3b8-b553-439b-a837-5940737f672a)

Users can use the ``manager`` role to distinguish between reference APIs and
operating APIs. This is an existing function of oslo.policy, and here is just a
suggested usage scenario.

``user-a`` has no ``manager`` role and cannot delete VIM.

.. code-block:: console

    $ openstack vim delete 95f633de-d2d1-4d90-90f7-0f3839369ff2
    Unable to delete the below vim(s):
    Cannot delete 95f633de-d2d1-4d90-90f7-0f3839369ff2: The resource could not be found.

``user-manager`` has the role of ``manager`` and can delete VIM.

.. code-block:: console

    $ openstack vim delete 95f633de-d2d1-4d90-90f7-0f3839369ff2
    All specified vim(s) deleted successfully

LIST resources
~~~~~~~~~~~~~~

For APIs that list resources, Enhanced Tacker Policy acts as a filter. That is,
the list operation only lists resources that the user has permission.
Here take List VIM as an example.

The ``user-a`` only has permission to access the VIM with area attribute
``tokyo@japan``. Therefore, ``user-a`` can only list the VIM with area
attribute ``tokyo@japan``.

.. code-block:: console

    $ openstack vim list
    +--------------------------------------+------------------------+----------------------------------+------------+------------+-----------+
    | ID                                   | Name                   | Tenant_id                        | Type       | Is Default | Status    |
    +--------------------------------------+------------------------+----------------------------------+------------+------------+-----------+
    | 705f23fc-054f-46c4-bcfe-922d11d85b27 | kubernetes-tokyo@japan | 4cdc4e2efe144f87812677cfe224fffb | kubernetes | False      | REACHABLE |
    | c5e82dd6-c5bc-4018-8415-ee5d53df5203 | default_for_nfv        | 4cdc4e2efe144f87812677cfe224fffb | openstack  | True       | REACHABLE |
    +--------------------------------------+------------------------+----------------------------------+------------+------------+-----------+

The ``user-b`` does not have access to any VIM with the area attribute, so
the list is empty when performing the List VIM operation.

.. code-block:: console

    $ openstack vim list
    (No output.)


The ``user-manager`` has access rights to all resources. It can list all
resources.

.. code-block:: console

    $ openstack vim list
    +--------------------------------------+------------------------+----------------------------------+------------+------------+-----------+
    | ID                                   | Name                   | Tenant_id                        | Type       | Is Default | Status    |
    +--------------------------------------+------------------------+----------------------------------+------------+------------+-----------+
    | 705f23fc-054f-46c4-bcfe-922d11d85b27 | kubernetes-tokyo@japan | 4cdc4e2efe144f87812677cfe224fffb | kubernetes | False      | REACHABLE |
    | c5e82dd6-c5bc-4018-8415-ee5d53df5203 | default_for_nfv        | 4cdc4e2efe144f87812677cfe224fffb | openstack  | True       | REACHABLE |
    | cd63517f-95c2-4088-ab67-36420ab87ed7 | openstack-osaka@japan  | 4cdc4e2efe144f87812677cfe224fffb | openstack  | False      | REACHABLE |
    +--------------------------------------+------------------------+----------------------------------+------------+------------+-----------+

Limitations
-----------
* As the resources created in the previous version of Tacker may not have
  enhanced policy attributes, if the enhanced policy attributes are used as
  comparison attributes in the policy rule, this rule will prevent users from
  accessing those resources without these attributes as the comparison result
  is always false.

Appendix
--------

Tacker APIs that support Enhanced Tacker Policy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The table below lists the APIs that support Enhanced Tacker Policy, and the
enhanced tacker attributes supported by each API.

.. list-table::
  :widths: 28 28 16 16 16
  :header-rows: 1

  * - Operation
    - API
    - Supports area
    - Supports vendor
    - Supports tenant
  * - VIM-List
    - **GET** /v1.0/vims
    - Yes
    - No
    - No
  * - VIM-Show
    - **GET** /v1.0/vims/{vim_id}
    - Yes
    - No
    - No
  * - VIM-Update
    - **PUT** /v1.0/vims/{vim_id}
    - Yes
    - No
    - No
  * - VIM-Delete
    - **Delete** /v1.0/vims/{vim_id}
    - Yes
    - No
    - No
  * - PKG-List
    - **GET** /vnfpkgm/v1/vnf_packages
    - No
    - Yes(1)
    - No
  * - PKG-Show
    - **GET** /vnfpkgm/v1/vnf_packages/{vnfPkgId}
    - No
    - Yes(1)
    - No
  * - PKG-Update
    - **PATCH** /vnfpkgm/v1/vnf_packages/{vnfPkgId}
    - No
    - Yes
    - No
  * - PKG-Delete
    - **DELETE** /vnfpkgm/v1/vnf_packages/{vnfPkgId}
    - No
    - Yes
    - No
  * - PKG-Read-vnfd
    - **GET** /vnfpkgm/v1/vnf_packages/{vnfPkgId}/vnfd
    - No
    - Yes
    - No
  * - PKG-Fetch
    - **GET** /vnfpkgm/v1/vnf_packages/{vnfPkgId}/package_content
    - No
    - Yes
    - No
  * - PKG-Upload-content
    - **PUT** /vnfpkgm/v1/vnf_packages/{vnfPkgId}/package_content
    - No
    - Yes
    - No
  * - PKG-Artifacts
    - **GET** /vnfpkgm/v1/vnf_packages/{vnfPkgId}/artifacts/{artifactPath}
    - No
    - Yes
    - No
  * - LCM-List
    - **GET** /vnflcm/v1/vnf_instances
    - Yes(3)
    - Yes
    - Yes(2)
  * - LCM-Create
    - **POST** /vnflcm/v1/vnf_instances
    - No
    - Yes
    - No
  * - LCM-Show
    - **GET** /vnflcm/v1/vnf_instances/{vnfInstanceId}
    - Yes(3)
    - Yes
    - Yes(2)
  * - LCM-Update
    - **PATCH** /vnflcm/v1/vnf_instances/{vnfInstanceId}
    - Yes
    - Yes
    - Yes(2)
  * - LCM-Delete
    - **DELETE** /vnflcm/v1/vnf_instances/{vnfInstanceId}
    - No
    - Yes
    - No
  * - LCM-Instantiate
    - **POST** /vnflcm/v1/vnf_instances/{vnfInstanceId}/instantiate
    - Yes
    - Yes
    - Yes(2)
  * - LCM-Scale
    - **POST** /vnflcm/v1/vnf_instances/{vnfInstanceId}/scale
    - Yes
    - Yes
    - Yes(2)
  * - LCM-Terminate
    - **POST** /vnflcm/v1/vnf_instances/{vnfInstanceId}/terminate
    - Yes
    - Yes
    - Yes(2)
  * - LCM-Heal
    - **POST** /vnflcm/v1/vnf_instances/{vnfInstanceId}/heal
    - Yes
    - Yes
    - Yes(2)
  * - LCM-Change-Connectivity
    - **POST** /vnflcm/v1/vnf_instances/{vnfInstanceId}/change_ext_conn
    - Yes
    - Yes
    - Yes(2)
  * - LCM-ListV2
    - **GET** /vnflcm/v2/vnf_instances
    - Yes(4)
    - Yes
    - Yes(2)
  * - LCM-CreateV2
    - **POST** /vnflcm/v2/vnf_instances
    - No
    - Yes
    - No
  * - LCM-ShowV2
    - **GET** /vnflcm/v2/vnf_instances/{vnfInstanceId}
    - Yes(4)
    - Yes
    - Yes(2)
  * - LCM-UpdateV2
    - **PATCH** /vnflcm/v2/vnf_instances/{vnfInstanceId}
    - Yes
    - Yes
    - Yes(2)
  * - LCM-DeleteV2
    - **DELETE** /vnflcm/v2/vnf_instances/{vnfInstanceId}
    - No
    - Yes
    - No
  * - LCM-InstantiateV2
    - **POST** /vnflcm/v2/vnf_instances/{vnfInstanceId}/instantiate
    - Yes
    - Yes
    - Yes(2)
  * - LCM-ScaleV2
    - **POST** /vnflcm/v2/vnf_instances/{vnfInstanceId}/scale
    - Yes
    - Yes
    - Yes(2)
  * - LCM-TerminateV2
    - **POST** /vnflcm/v2/vnf_instances/{vnfInstanceId}/terminate
    - Yes
    - Yes
    - Yes(2)
  * - LCM-HealV2
    - **POST** /vnflcm/v2/vnf_instances/{vnfInstanceId}/heal
    - Yes
    - Yes
    - Yes(2)
  * - LCM-Change-ConnectivityV2
    - **POST** /vnflcm/v2/vnf_instances/{vnfInstanceId}/change_ext_conn
    - Yes
    - Yes
    - Yes(2)
  * - LCM-Change-VnfPkgV2
    - **POST** /vnflcm/v2/vnf_instances/{vnfInstanceId}/change_vnfpkg
    - Yes
    - Yes
    - Yes(2)

(1) This is ignored when the state is not `ONBOARDED`.
(2) This is ignored when the instance is vnf(not cnf).
(3) Default vim is used when the state is `NOT_INSTANTIATED`.
(4) This is ignored when the state is not `NOT_INSTANTIATED`.

Sample policy.yaml file
~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../etc/tacker/enhanced_tacker_policy.yaml.sample

References
----------

.. [#oslo.policy] https://docs.openstack.org/oslo.policy/latest/
.. [#VIM_Management] https://docs.openstack.org/tacker/latest/cli/cli-legacy-vim.html
.. [#VNF_Package] https://docs.openstack.org/tacker/latest/user/vnf-package.html
.. [#VNF_Lifecycle_Management] https://docs.openstack.org/tacker/latest/cli/cli-etsi-vnflcm.html
