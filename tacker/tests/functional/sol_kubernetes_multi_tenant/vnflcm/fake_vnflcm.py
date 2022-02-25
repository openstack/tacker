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

from tacker.tests import uuidsentinel


class Subscription:

    @staticmethod
    def make_create_request_body(callback_uri):
        """Parameter selection policy.

        Set all Notification types and all life cycle types for filter.
        Specify OAuth2 for authentication → do not set authentication.

        Args:
            callback_uri (str): Notification URI.

        Returns:
            dict: Request body
        """
        return {
            "filter": {
                "vnfInstanceSubscriptionFilter": {
                    "vnfdIds": ["b1bb0ce7-ebca-4fa7-95ed-4840d7000000"],
                    "vnfProductsFromProviders": [{
                        "vnfProvider": "Company",
                        "vnfProducts": [
                            {
                                "vnfProductName": "Sample VNF",
                                "versions": [
                                    {
                                        "vnfSoftwareVersion": "1.0",
                                        "vnfdVersions": ["1.0"]
                                    }
                                ]
                            }
                        ]
                    }]
                },
                "notificationTypes": [
                    "VnfLcmOperationOccurrenceNotification",
                    "VnfIdentifierCreationNotification",
                    "VnfIdentifierDeletionNotification"
                ],
                "operationTypes": [
                    "INSTANTIATE",
                    "SCALE",
                    "TERMINATE",
                    "HEAL",
                    "MODIFY_INFO",
                    "CHANGE_EXT_CONN"
                ],
                "operationStates": ["STARTING"]
            },
            "callbackUri": callback_uri
        }


class VnfInstances:

    @staticmethod
    def make_create_request_body(vnfd_id):
        return {
            "vnfdId": vnfd_id,
            "vnfInstanceName": "",
            "vnfInstanceDescription": "Sample VNF",
            "metadata": {
                "samplekey": "samplevalue"
            }
        }

    @staticmethod
    def make_inst_request_body(vim_id, additional_params):
        data = {
            "flavourId": "simple",
            "vimConnectionInfo": [{
                "id": uuidsentinel.vim_connection_id,
                "vimType": "kubernetes",
                "vimId": vim_id
            }],
            "additionalParams": additional_params
        }

        return data

    @staticmethod
    def make_term_request_body():
        """Parameter selection policy.

        As all parameters are set, GRACEFUL is specified for terminationType.
        (to specify gracefulTerminationTimeout)

        Returns:
            dict: Request body
        """
        return {
            "terminationType": "FORCEFUL"
        }
