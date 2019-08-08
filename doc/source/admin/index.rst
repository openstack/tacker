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

The following list covers the commands for Tacker services available in
**openstack** command.

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
