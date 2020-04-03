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

from tacker.api import views as base
from tacker.objects import vnf_package as _vnf_package


class ViewBuilder(base.BaseViewBuilder):

    FLATTEN_ATTRIBUTES = _vnf_package.VnfPackage.FLATTEN_ATTRIBUTES
    COMPLEX_ATTRIBUTES = _vnf_package.VnfPackage.COMPLEX_ATTRIBUTES
    FLATTEN_COMPLEX_ATTRIBUTES = [key for key in FLATTEN_ATTRIBUTES.keys()
        if '/' in key]

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

    def _get_vnf_package(self, vnf_package, include_fields=None):
        vnf_package_response = vnf_package.to_dict(
            include_fields=include_fields)

        links = self._get_links(vnf_package)
        vnf_package_response.update(links)

        return vnf_package_response

    def _get_modified_user_data(self, old_user_data, new_user_data):
        # Checking for the new keys
        user_data_response = {k: new_user_data[k] for k
                              in set(new_user_data) - set(old_user_data)}

        # Checking for updation in values of existing keys
        for old_key, old_value in old_user_data.items():
            if old_key in new_user_data.keys() and \
                    new_user_data[old_key] != old_user_data[old_key]:
                user_data_response[old_key] = new_user_data[old_key]

        return user_data_response

    def create(self, request, vnf_package):
        return self._get_vnf_package(vnf_package)

    def show(self, request, vnf_package):
        return self._get_vnf_package(vnf_package)

    def patch(self, vnf_package, new_vnf_package):
        response = {}
        if vnf_package.operational_state != new_vnf_package.operational_state:
            response['operationalState'] = new_vnf_package.operational_state
        if vnf_package.user_data != new_vnf_package.user_data:
            updated_user_data = self._get_modified_user_data(
                vnf_package.user_data, new_vnf_package.user_data)
            response['userDefinedData'] = updated_user_data

        return response

    def index(self, request, vnf_packages, all_fields=True,
            exclude_fields=None, fields=None, exclude_default=False):

        # Find out which fields are to be returned in the response.
        if all_fields:
            include_fields = set(self.FLATTEN_ATTRIBUTES.keys())
        if exclude_default and fields or fields:
            # Note(tpatil): If fields contains any of the complex attributes
            # base name, it should include all attributes from that complex
            # attribute. For example, if softwareImages is passed in the
            # fields, it should include all attributes matching
            # softwareImages/*.
            fields = set(fields.split(','))
            attributes = set(self.COMPLEX_ATTRIBUTES).intersection(fields)
            for attribute in attributes:
                add_fields = set([key for key in self.FLATTEN_ATTRIBUTES.
                    keys() if key.startswith(attribute)])
                fields = fields.union(add_fields)

            include_fields = set(_vnf_package.VnfPackage.simple_attributes +
                _vnf_package.VnfPackage.simple_instantiated_attributes). \
                union(fields)
        elif exclude_default:
            include_fields = set(_vnf_package.VnfPackage.simple_attributes +
                _vnf_package.VnfPackage.simple_instantiated_attributes)
        elif exclude_fields:
            # Note(tpatil): If exclude_fields contains any of the complex
            # attributes base name, it should exclude all attributes from
            # that complex attribute. For example, if softwareImages is passed
            # in the excluded_fields, it should exclude all attributes
            # matching softwareImages/*.
            exclude_fields = set(exclude_fields.split(','))
            exclude_additional_attributes = set(
                self.COMPLEX_ATTRIBUTES).intersection(exclude_fields)
            for attribute in exclude_additional_attributes:
                fields = set([key for key in self.FLATTEN_ATTRIBUTES.keys()
                    if key.startswith(attribute)])
                exclude_fields = exclude_fields.union(fields)

            include_fields = set(self.FLATTEN_ATTRIBUTES.keys()) - \
                exclude_fields
        return [self._get_vnf_package(vnf_package,
            include_fields=include_fields)for vnf_package in vnf_packages]
