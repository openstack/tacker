#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
from oslo_utils import uuidutils


class VnfPackage:
    VNF_PACKAGE_REQ_PATH = "/vnfpkgm/v1/vnf_packages"

    @staticmethod
    def make_list_response_body():
        return [VnfPackage.make_individual_response]

    @staticmethod
    def make_individual_response_body(vnfd_id, vnf_package_hash):
        add_artifact_hash = (
            "6513f21e44aa3da349f248188a44" +
            "bc304a3653a04122d8fb4535423c8" +
            "e1d14cd6a153f735bb0982e2" +
            "161b5b5186106570c17a9" +
            "e58b64dd39390617cd5a350f78")

        sw_image_hash = (
            "6513f21e44aa3da349" +
            "f248188a44bc304a3653a04" +
            "122d8fb4535423c8e1d14c" +
            "d6a153f735bb0982e2161b5" +
            "b5186106570c17a9e58b6" +
            "4dd39390617cd5a350f78")

        data = {
            "id": uuidutils.generate_uuid(),
            "vnfdId": vnfd_id,
            "vnfProvider": "Company",
            "vnfProductName": "Sample VNF",
            "vnfSoftwareVersion": "1.0",
            "vnfdVersion": "1.0",
            "checksum": {
                "algorithm": "SHA-512",
                "hash": vnf_package_hash
            },
            "softwareImages": [
                {
                    "id": "sw_image",
                    "name": "cirros-0.5.2-x86_64-disk",
                    "provider": "Company",
                    "version": "0.5.2",
                    "checksum": {
                        "algorithm": "SHA-512",
                        "hash": sw_image_hash
                    },
                    "containerFormat": "BARE",
                    "diskFormat": "QCOW2",
                    "createdAt": "2020-09-01T12:34:56Z",
                    "minDisk": "2147483648",
                    "minRam": "268435456",
                    "size": "1073741824",
                    "userMetadata": {
                        "key": "value"
                    },
                    "imagePath": "Files/images/cirros-0.5.2-x86_64-disk.img"
                }
            ],
            "additionalArtifacts": [
                {
                    "artifactPath":
                        "Files/images/cirros-0.5.2-x86_64-disk.img",
                    "checksum": {
                        "algorithm": "SHA-512",
                        "hash": add_artifact_hash
                    },
                    "metadata": {
                        "key": "value"
                    }
                }
            ],
            "onboardingState": "ONBOARDED",
            "operationalState": "ENABLED",
            "usageState": "NOT_IN_USE",
            "userDefinedData": {
                "key": "value"
            },
            "_links": {
                "self": {
                    "href": "GetPackage URI"
                },
                "vnfd": {
                    "href": "GetVNFD URI"
                },
                "packageContent": {
                    "href": "GetPackageContent URI"
                }
            }
        }

        return data
