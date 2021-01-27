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
                    "MODIFY_INFO"
                ]
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
    def make_inst_request_body(
            tenant_id,
            networks_id,
            ext_mngd_networks_id,
            external_ports_id,
            external_subnets_id):
        ext_vdu1_cp1 = {
            "cpdId": "VDU1_CP1",
            "cpConfig": [{
                "linkPortId": uuidsentinel.elp1_id
            }],
        }
        ext_vdu2_cp1 = {
            "cpdId": "VDU2_CP1",
            "cpConfig": [{
                "linkPortId": uuidsentinel.elp2_id
            }]
        }

        # set external port_id on vim.
        ext_link_port1 = {
            "id": uuidsentinel.elp1_id,
            "resourceHandle": {
                "vimConnectionId": uuidsentinel.vim_connection_id,
                "resourceId": external_ports_id[0]
            }
        }
        ext_link_port2 = {
            "id": uuidsentinel.elp2_id,
            "resourceHandle": {
                "vimConnectionId": uuidsentinel.vim_connection_id,
                "resourceId": external_ports_id[1]
            }
        }
        ext_virtual_link_cp1 = {
            "id": uuidsentinel.evl1_id,
            # set external nw_id on vim.
            "resourceId": networks_id[0],
            "extCps": [ext_vdu1_cp1, ext_vdu2_cp1],
            "extLinkPorts": [ext_link_port1, ext_link_port2]
        }

        # set external subet_id on vim.
        ext_cps_vdu1_cp2 = {
            "cpdId": "VDU1_CP2",
            "cpConfig": [{
                "cpProtocolData": [{
                    "layerProtocol": "IP_OVER_ETHERNET",
                    "ipOverEthernet": {
                        "ipAddresses": [{
                            "type": "IPV4",
                            "fixedAddresses": ["22.22.2.10"],
                            "subnetId": external_subnets_id[0]
                        }]
                    }
                }]
            }]
        }
        # set external subet_id on vim.
        ext_cps_vdu2_cp2 = {
            "cpdId": "VDU2_CP2",
            "cpConfig": [{
                "cpProtocolData": [{
                    "layerProtocol": "IP_OVER_ETHERNET",
                    "ipOverEthernet": {
                        "ipAddresses": [{
                            "type": "IPV4",
                            "fixedAddresses": ["22.22.2.20"],
                            "subnetId": external_subnets_id[1]
                        }]
                    }
                }]
            }]
        }

        ext_virtual_link_cp2 = {
            "id": uuidsentinel.evl2_id,
            "resourceId": networks_id[1],
            "extCps": [
                ext_cps_vdu1_cp2, ext_cps_vdu2_cp2
            ]
        }

        # set extManaged internal nw_id on vim.
        ext_mng_vtl_lnks = [{
            "id": uuidsentinel.emvl1_id,
            "vnfVirtualLinkDescId": "internalVL1",
            "resourceId": ext_mngd_networks_id[0]
        }, {
            "id": uuidsentinel.emvl2_id,
            "vnfVirtualLinkDescId": "internalVL2",
            "resourceId": ext_mngd_networks_id[1]
        }]

        data = {
            "flavourId": "simple",
            "instantiationLevelId": "instantiation_level_1",
            "extVirtualLinks": [
                ext_virtual_link_cp1, ext_virtual_link_cp2
            ],
            "extManagedVirtualLinks": ext_mng_vtl_lnks,
            "vimConnectionInfo": [{
                "id": uuidsentinel.vim_connection_id,
                "vimType": "ETSINFV.OPENSTACK_KEYSTONE.v_2",
                "vimConnectionId": uuidsentinel.vim_connection_id,
                "interfaceInfo": {
                    "endpoint": "http://127.0.0.1/identity"
                },
                "accessInfo": {
                    "username": "nfv_user",
                    "region": "RegionOne",
                    "password": "devstack",
                    "tenant": tenant_id
                }
            }],
            "additionalParams": {
                "lcm-operation-user-data": "./UserData/lcm_user_data.py",
                "lcm-operation-user-data-class": "SampleUserData"
            }
        }

        return data

    @staticmethod
    def make_heal_request_body(vnfc_instance_id=None):
        data = {
            "cause": "ManualHealing"
        }
        if vnfc_instance_id:
            data["vnfcInstanceId"] = vnfc_instance_id

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
            "terminationType": "GRACEFUL",
            "gracefulTerminationTimeout": 1,
            "additionalParams": {
                "samplekey": "samplevalue"
            }
        }

    @staticmethod
    def make_update_request_body(vnfd_id=None, vnf_package_id=None):
        """Parameter selection policy.

        vimConnectionInfo is not set.

        Args:
            vnfd_id (str, optional): vnfdId(2.6.1)
            vnf_package_id (str, optional): vnfPkgId(2.4.1)

        Returns:
            dict: Request body
        """
        data = {
            "vnfInstanceName": "helloworld3_modify",
            "vnfInstanceDescription": "Sample VNF Modify",
            "metadata": {
                "samplekey": "samplevalue_modified"
            }
        }

        if vnfd_id:
            data["vnfdId"] = vnfd_id
        elif vnf_package_id:
            data["vnfPkgId"] = vnf_package_id

        return data

    def make_scale_request_body(scale_type):
        """Parameter selection policy.

        numberOfSteps specifies 1

        Args:
            scale_type (str): SCALE_OUT or SCALE_IN
        """

        return {
            "type": scale_type,
            "aspectId": "VDU1_scale",
            "numberOfSteps": 1,
            "additionalParams": {
                "samplekey": "samplevalue"
            }
        }
