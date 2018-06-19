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

==================
Tacker Admin Guide
==================

There are two Command-Line Interfaces (CLIs) which support the Tacker API:
`OpenStackClient (OSC)
<https://docs.openstack.org/python-openstackclient/latest/>`__
and `tacker CLI <tacker>`.

.. note::

   Deprecated: 'tacker' command line is deprecated, will be deleted after
   Rocky is released. Please use 'openstack' client command line instead.

Tacker CLI
----------

.. code-block:: console

    usage: tacker [--version] [-v] [-q] [-h] [-r NUM]
              [--os-service-type <os-service-type>]
              [--os-endpoint-type <os-endpoint-type>]
              [--service-type <service-type>]
              [--endpoint-type <endpoint-type>]
              [--os-auth-strategy <auth-strategy>] [--os-auth-url <auth-url>]
              [--os-tenant-name <auth-tenant-name> | --os-project-name <auth-project-name>]
              [--os-tenant-id <auth-tenant-id> | --os-project-id <auth-project-id>]
              [--os-username <auth-username>] [--os-user-id <auth-user-id>]
              [--os-user-domain-id <auth-user-domain-id>]
              [--os-user-domain-name <auth-user-domain-name>]
              [--os-project-domain-id <auth-project-domain-id>]
              [--os-project-domain-name <auth-project-domain-name>]
              [--os-cert <certificate>] [--os-cacert <ca-certificate>]
              [--os-key <key>] [--os-password <auth-password>]
              [--os-region-name <auth-region-name>] [--os-token <token>]
              [--http-timeout <seconds>] [--os-url <url>] [--insecure]

    Command-line interface to the Tacker APIs

    optional arguments:
      --version             show program's version number and exit
      -v, --verbose, --debug
                            Increase verbosity of output and show tracebacks on
                            errors. You can repeat this option.
      -q, --quiet           Suppress output except warnings and errors.
      -h, --help            Show this help message and exit.
      -r NUM, --retries NUM
                            How many times the request to the Tacker server should
                            be retried if it fails.
      --os-service-type <os-service-type>
                            Defaults to env[OS_TACKER_SERVICE_TYPE] or nfv-
                            orchestration.
      --os-endpoint-type <os-endpoint-type>
                            Defaults to env[OS_ENDPOINT_TYPE] or publicURL.
      --service-type <service-type>
                            DEPRECATED! Use --os-service-type.
      --endpoint-type <endpoint-type>
                            DEPRECATED! Use --os-endpoint-type.
      --os-auth-strategy <auth-strategy>
                            DEPRECATED! Only keystone is supported.
      --os-auth-url <auth-url>
                            Authentication URL, defaults to env[OS_AUTH_URL].
      --os-tenant-name <auth-tenant-name>
                            Authentication tenant name, defaults to
                            env[OS_TENANT_NAME].
      --os-project-name <auth-project-name>
                            Another way to specify tenant name. This option is
                            mutually exclusive with --os-tenant-name. Defaults to
                            env[OS_PROJECT_NAME].
      --os-tenant-id <auth-tenant-id>
                            Authentication tenant ID, defaults to
                            env[OS_TENANT_ID].
      --os-project-id <auth-project-id>
                            Another way to specify tenant ID. This option is
                            mutually exclusive with --os-tenant-id. Defaults to
                            env[OS_PROJECT_ID].
      --os-username <auth-username>
                            Authentication username, defaults to env[OS_USERNAME].
      --os-user-id <auth-user-id>
                            Authentication user ID (Env: OS_USER_ID)
      --os-user-domain-id <auth-user-domain-id>
                            OpenStack user domain ID. Defaults to
                            env[OS_USER_DOMAIN_ID].
      --os-user-domain-name <auth-user-domain-name>
                            OpenStack user domain name. Defaults to
                            env[OS_USER_DOMAIN_NAME].
      --os-project-domain-id <auth-project-domain-id>
                            Defaults to env[OS_PROJECT_DOMAIN_ID].
      --os-project-domain-name <auth-project-domain-name>
                            Defaults to env[OS_PROJECT_DOMAIN_NAME].
      --os-cert <certificate>
                            Path of certificate file to use in SSL connection.
                            This file can optionally be prepended with the private
                            key. Defaults to env[OS_CERT].
      --os-cacert <ca-certificate>
                            Specify a CA bundle file to use in verifying a TLS
                            (https) server certificate. Defaults to
                            env[OS_CACERT].
      --os-key <key>        Path of client key to use in SSL connection. This
                            option is not necessary if your key is prepended to
                            your certificate file. Defaults to env[OS_KEY].
      --os-password <auth-password>
                            Authentication password, defaults to env[OS_PASSWORD].
      --os-region-name <auth-region-name>
                            Authentication region name, defaults to
                            env[OS_REGION_NAME].
      --os-token <token>    Authentication token, defaults to env[OS_TOKEN].
      --http-timeout <seconds>
                            Timeout in seconds to wait for an HTTP response.
                            Defaults to env[OS_NETWORK_TIMEOUT] or None if not
                            specified.
      --os-url <url>        Defaults to env[OS_URL].
      --insecure            Explicitly allow tackerclient to perform "insecure"
                            SSL (https) requests. The server's certificate will
                            not be verified against any certificate authorities.
                            This option should be used with caution.

    Commands for API v1.0:
      bash-completion        Prints all of the commands and options for bash-completion.
      chain-list             List SFCs that belong to a given tenant.
      chain-show             Show information of a given SFC.
      classifier-list        List FCs that belong to a given tenant.
      classifier-show        Show information of a given FC.
      cluster-create         Create a Cluster.
      cluster-delete         Delete a given Cluster.
      cluster-list           List Clusters that belong to a given tenant.
      cluster-member-add     Add a new Cluster Member to given Cluster.
      cluster-member-delete  Delete a given Cluster Member.
      cluster-member-list    List Cluster Members that belong to a given tenant.
      cluster-member-show    Show information of a given Cluster Member.
      cluster-show           Show information of a given Cluster.
      event-show             Show event given the event id.
      events-list            List events of resources.
      ext-list               List all extensions.
      ext-show               Show information of a given resource.
      help                   print detailed help for another command
      nfp-list               List NFPs that belong to a given tenant.
      nfp-show               Show information of a given NFP.
      ns-create              Create a NS.
      ns-delete              Delete given NS(s).
      ns-list                List NS that belong to a given tenant.
      ns-show                Show information of a given NS.
      nsd-create             Create a NSD.
      nsd-delete             Delete a given NSD.
      nsd-list               List NSDs that belong to a given tenant.
      nsd-show               Show information of a given NSD.
      nsd-template-show      Show template of a given NSD.
      vim-delete             Delete given VIM(s).
      vim-events-list        List events of VIMs.
      vim-list               List VIMs that belong to a given tenant.
      vim-register           Create a VIM.
      vim-show               Show information of a given VIM.
      vim-update             Update a given VIM.
      vnf-create             Create a VNF.
      vnf-delete             Delete given VNF(s).
      vnf-events-list        List events of VNFs.
      vnf-list               List VNF that belong to a given tenant.
      vnf-resource-list      List resources of a VNF like VDU, CP, etc.
      vnf-scale              Scale a VNF.
      vnf-show               Show information of a given VNF.
      vnf-update             Update a given VNF.
      vnfd-create            Create a VNFD.
      vnfd-delete            Delete given VNFD(s).
      vnfd-events-list       List events of VNFDs.
      vnfd-list              List VNFD that belong to a given tenant.
      vnfd-show              Show information of a given VNFD.
      vnfd-template-show     Show template of a given VNFD.
      vnffg-create           Create a VNFFG.
      vnffg-delete           Delete a given VNFFG.
      vnffg-list             List VNFFGs that belong to a given tenant.
      vnffg-show             Show information of a given VNFFG.
      vnffg-update           Update a given VNFFG.
      vnffgd-create          Create a VNFFGD.
      vnffgd-delete          Delete a given VNFFGD.
      vnffgd-list            List VNFFGDs that belong to a given tenant.
      vnffgd-show            Show information of a given VNFFGD.
      vnffgd-template-show   Show template of a given VNFFGD.


OpenStackClient CLI
-------------------

The following list covers the extended commands for Tacker services
available in **openstack** command.

These commands can be referenced by doing **openstack help** and the detail
of individual command can be referred by **openstack help <command-name>**.

.. code-block:: console

   openstack vnf create                            Create a VNF.
   openstack vnf delete                            Delete given VNF(s).
   openstack vnf list                              List VNF(s) that belong to a given tenant.
   openstack vnf resource list                     List resources of a VNF like VDU, CP, etc.
   openstack vnf scale                             Scale a VNF.
   openstack vnf show                              Show information of a given VNF.
   openstack vnf set                               Update a given VNF.
   openstack vnf descriptor create                 Create a VNFD.
   openstack vnf descriptor delete                 Delete given VNFD(s).
   openstack vnf descriptor list                   List VNFD(s) that belong to a given tenant.
   openstack vnf descriptor show                   Show information of a given VNFD.
   openstack vnf descriptor template show          Show template of a given VNFD.
   openstack vim list                              List VIM(s) that belong to a given tenant.
   openstack vim register                          Create a VIM.
   openstack vim show                              Show information of a given VIM.
   openstack vim set                               Update a given VIM.
   openstack vim delete                            Delete given VIM(s).
   openstack ns create                             Create a NS.
   openstack ns delete                             Delete given NS(s).
   openstack ns list                               List NS that belong to a given tenant.
   openstack ns show                               Show information of a given NS.
   openstack ns descriptor create                  Create a NSD.
   openstack ns descriptor delete                  Delete a given NSD.
   openstack ns descriptor list                    List NSD(s) that belong to a given tenant.
   openstack ns descriptor show                    Show information of a given NSD.
   openstack ns descriptor template show           Show template of a given NSD.
   openstack vnf graph create                      Create a VNFFG.
   openstack vnf graph delete                      Delete a given VNFFG.
   openstack vnf graph list                        List VNFFG(s) that belong to a given tenant.
   openstack vnf graph show                        Show information of a given VNFFG.
   openstack vnf graph set                         Update a given VNFFG.
   openstack vnf graph descriptor create           Create a VNFFGD.
   openstack vnf graph descriptor delete           Delete a given VNFFGD.
   openstack vnf graph descriptor list             List VNFFGD(s) that belong to a given tenant.
   openstack vnf graph descriptor show             Show information of a given VNFFGD.
   openstack vnf graph descriptor template show    Show template of a given VNFFGD.
   openstack vnf chain list                        List SFC(s) that belong to a given tenant.
   openstack vnf chain show                        Show information of a given SFC.
   openstack vnf classifier list                   List FC(s) that belong to a given tenant.
   openstack vnf classifier show                   Show information of a given FC.
   openstack vnf network forwarding path list      List NFP(s) that belong to a given tenant.
   openstack vnf network forwarding path show      Show information of a given NFP.
   openstack nfv event show                        Show event given the event id.
   openstack nfv event list                        List events of resources.

