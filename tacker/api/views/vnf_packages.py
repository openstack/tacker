# Copyright (C) 2019 NTT DATA
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from tacker.objects import fields


class ViewBuilder(object):

    def _get_links(self, vnf_package):
        return {
            "_links": {
                "self": {
                    "href": '/vnfpkgm/v1/vnf_packages/%s'
                            % vnf_package.id
                },
                "packageContent": {
                    "href": '/vnfpkgm/v1/vnf_packages/%s/package_content'
                            % vnf_package.id
                }
            }
        }

    def _get_software_images(self, vnf_deployment_flavours):
        software_images = list()
        for vnf_deployment_flavour in vnf_deployment_flavours:
            for sw_image in vnf_deployment_flavour.software_images:
                software_images.append({
                    "id": sw_image.software_image_id,
                    "name": sw_image.name,
                    "provider": "provider",
                    "version": sw_image.version,
                    "checksum": {
                        "algorithm": sw_image.algorithm,
                        "hash": sw_image.hash
                    },
                    "containerFormat": sw_image.container_format,
                    "diskFormat": sw_image.disk_format,
                    "minDisk": sw_image.min_disk,
                    "minRam": sw_image.min_ram,
                    "size": sw_image.size,
                    "imagePath": sw_image.image_path,
                    "userMetadata": sw_image.metadata
                })

        return {'softwareImages': software_images}

    def _get_vnfd(self, vnf_package):
        vnfd = vnf_package.vnfd
        return {
            'vnfdId': vnfd.vnfd_id,
            'vnfProvider': vnfd.vnf_provider,
            'vnfProductName': vnfd.vnf_product_name,
            'vnfSoftwareVersion': vnfd.vnf_software_version,
            'vnfdVersion': vnfd.vnfd_version
        }

    def _basic_vnf_package_info(self, vnf_package):
        return {
            'id': vnf_package.id,
            'onboardingState': vnf_package.onboarding_state,
            'operationalState': vnf_package.operational_state,
            'usageState': vnf_package.usage_state,
            'userDefinedData': vnf_package.user_data,
        }

    def _get_vnf_package(self, vnf_package):
        vnf_package_response = self._basic_vnf_package_info(vnf_package)

        links = self._get_links(vnf_package)
        vnf_package_response.update(links)

        if (vnf_package.onboarding_state ==
                fields.PackageOnboardingStateType.ONBOARDED):
            # add software images
            vnf_deployment_flavours = vnf_package.vnf_deployment_flavours
            vnf_package_response.update(self._get_software_images(
                vnf_deployment_flavours))

            vnf_package_response.update(self._get_vnfd(vnf_package))

        return vnf_package_response

    def create(self, request, vnf_package):

        return self._get_vnf_package(vnf_package)

    def show(self, request, vnf_package):

        return self._get_vnf_package(vnf_package)

    def index(self, request, vnf_packages):
        return {'vnf_packages': [self._get_vnf_package(
            vnf_package) for vnf_package in vnf_packages]}
