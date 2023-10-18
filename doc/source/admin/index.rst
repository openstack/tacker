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

  [legacy]
   openstack vim delete                        Delete given VIM(s).
   openstack vim list                          List VIM(s) in a given tenant.
   openstack vim register                      Create a VIM.
   openstack vim set                           Update a given VIM.
   openstack vim show                          Show information of a given VIM.

  [v1] --os-tacker-api-version 1
   openstack vnf package artifact download     Download VNF package artifact.
   openstack vnf package create                Create a new VNF Package.
   openstack vnf package delete                Delete VNF Package.
   openstack vnf package download              Download VNF package.
   openstack vnf package list                  List VNF Packages.
   openstack vnf package show                  Show VNF Package Details.
   openstack vnf package update                Update a VNF package.
   openstack vnf package upload                Upload VNF Package.
   openstack vnflcm change-ext-conn            Change External VNF Connectivity.
   openstack vnflcm create                     Create a new VNF Instance.
   openstack vnflcm delete                     Delete VNF Instance(s).
   openstack vnflcm heal                       Heal VNF Instance.
   openstack vnflcm instantiate                Instantiate a VNF Instance.
   openstack vnflcm list                       List VNF Instance.
   openstack vnflcm op cancel                  Cancel VNF Instance.
   openstack vnflcm op fail                    Fail VNF Instance.
   openstack vnflcm op list                    List LCM Operation Occurrences.
   openstack vnflcm op retry                   Retry VNF Instance.
   openstack vnflcm op rollback                Rollback VNF Instance.
   openstack vnflcm op show                    Display Operation Occurrence details.
   openstack vnflcm scale                      Scale a VNF Instance.
   openstack vnflcm show                       Display VNF instance details.
   openstack vnflcm subsc create               Create a new Lccn Subscription.
   openstack vnflcm subsc delete               Delete Lccn Subscription(s).
   openstack vnflcm subsc list                 List Lccn Subscriptions.
   openstack vnflcm subsc show                 Display Lccn Subscription details.
   openstack vnflcm terminate                  Terminate a VNF instance.
   openstack vnflcm update                     Update VNF Instance.
   openstack vnflcm versions                   Show VnfLcm Api versions.

  [v2] --os-tacker-api-version 2
   openstack vnflcm change-ext-conn            Change External VNF Connectivity.
   openstack vnflcm change-vnfpkg              Change Current VNF Package.
   openstack vnflcm create                     Create a new VNF Instance.
   openstack vnflcm delete                     Delete VNF Instance(s)
   openstack vnflcm heal                       Heal VNF Instance
   openstack vnflcm instantiate                Instantiate a VNF Instance.
   openstack vnflcm list                       List VNF Instance.
   openstack vnflcm op fail                    Fail VNF Instance.
   openstack vnflcm op list                    List LCM Operation Occurrences.
   openstack vnflcm op retry                   Retry VNF Instance.
   openstack vnflcm op rollback                Rollback VNF Instance.
   openstack vnflcm op show                    Display Operation Occurrence details.
   openstack vnflcm scale                      Scale a VNF Instance.
   openstack vnflcm show                       Display VNF instance details.
   openstack vnflcm subsc create               Create a new Lccn Subscription.
   openstack vnflcm subsc delete               Delete Lccn Subscription(s).
   openstack vnflcm subsc list                 List Lccn Subscriptions.
   openstack vnflcm subsc show                 Display Lccn Subscription details.
   openstack vnflcm terminate                  Terminate a VNF instance.
   openstack vnflcm update                     Update VNF Instance.
   openstack vnflcm versions                   Show VnfLcm Api versions.
   openstack vnffm alarm listn                 List VNF FM alarms.
   openstack vnffm alarm show                  Display VNF FM alarm details.
   openstack vnffm alarm update                Update a VNF FM alarm information.
   openstack vnffm sub create                  Create a new VNF FM subscription.
   openstack vnffm sub delete                  Delete VNF FM subscription(s).
   openstack vnffm sub list                    List VNF FM subs.
   openstack vnffm sub show                    Display VNF FM subscription details.
   openstack vnfpm job create                  Create a new VNF PM job.
   openstack vnfpm job delete                  Delete VNF PM job.
   openstack vnfpm job list                    List VNF PM jobs.
   openstack vnfpm job show                    Display VNF PM job details.
   openstack vnfpm job update                  Update a VNF PM job information.
   openstack vnfpm report show                 Display VNF PM report details.
   openstack vnfpm threshold create            Create a new VNF PM threshold.
   openstack vnfpm threshold delete            Delete VNF PM threshold.
   openstack vnfpm threshold list              List VNF PM thresholds.
   openstack vnfpm threshold show              Display VNF PM threshold details.
   openstack vnfpm threshold update            Update a VNF PM threshold information.
