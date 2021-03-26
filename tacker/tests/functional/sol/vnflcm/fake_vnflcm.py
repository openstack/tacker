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
                    "vnfProductsFromProviders": {
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
                    }
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


def _set_ext_link_port1(external_ports_id):
    ext_link_port1 = {
        "id": uuidsentinel.elp1_id,
        "resourceHandle": {
            "vimConnectionId": uuidsentinel.vim_connection_id,
            "resourceId": external_ports_id[0]
        }
    }
    return ext_link_port1


def _set_ext_link_port2(external_ports_id):
    ext_link_port2 = {
        "id": uuidsentinel.elp2_id,
        "resourceHandle": {
            "vimConnectionId": uuidsentinel.vim_connection_id,
            "resourceId": external_ports_id[1]
        }
    }
    return ext_link_port2


def _set_ext_virtual_link_cp1(networks_id, external_ports_id):
    ext_virtual_link_cp1 = {
        "id": uuidsentinel.evl1_id,
        "resourceId": networks_id[0],
        "extCps": [ext_vdu1_cp1, ext_vdu2_cp1],
        "extLinkPorts": [
            _set_ext_link_port1(external_ports_id),
            _set_ext_link_port2(external_ports_id)]
    }
    return ext_virtual_link_cp1


def _set_ext_cps_vdu1_cp2(external_subnets_id):
    ext_cps_vdu1_cp2 = {
        "cpdId": "VDU1_CP2",
        "cpConfig": [{
            "cpProtocolData": [{
                "layerProtocol": "IP_OVER_ETHERNET",
                "ipOverEthernet": {
                    "ipAddresses": [{
                        "type": "IPV4",
                        "fixedAddresses": ["22.22.1.10"],
                        "subnetId": external_subnets_id[1]
                    }]
                }
            }]
        }]
    }
    return ext_cps_vdu1_cp2


def _set_ext_cps_vdu2_cp2(external_subnets_id):
    ext_cps_vdu2_cp2 = {
        "cpdId": "VDU2_CP2",
        "cpConfig": [{
            "cpProtocolData": [{
                "layerProtocol": "IP_OVER_ETHERNET",
                "ipOverEthernet": {
                    "ipAddresses": [{
                        "type": "IPV4",
                        "fixedAddresses": ["22.22.1.20"],
                        "subnetId": external_subnets_id[1]
                    }]
                }
            }]
        }]
    }
    return ext_cps_vdu2_cp2


def _set_ext_cps_vdu1_cp2_in_num_dynamic(external_subnets_id):
    ext_cps_vdu1_cp2_in_num_dynamic = {
        "cpdId": "VDU1_CP2",
        "cpConfig": [{
            "cpProtocolData": [{
                "layerProtocol": "IP_OVER_ETHERNET",
                "ipOverEthernet": {
                    "ipAddresses": [{
                        "type": "IPV4",
                        "numDynamicAddresses": 1,
                        "subnetId": external_subnets_id[1]
                    }]
                }
            }]
        }]
    }
    return ext_cps_vdu1_cp2_in_num_dynamic


def _set_ext_cps_vdu2_cp2_in_num_dynamic(external_subnets_id):
    ext_cps_vdu2_cp2_in_num_dynamic = {
        "cpdId": "VDU2_CP2",
        "cpConfig": [{
            "cpProtocolData": [{
                "layerProtocol": "IP_OVER_ETHERNET",
                "ipOverEthernet": {
                    "ipAddresses": [{
                        "type": "IPV4",
                        "fixedAddresses": ["22.22.1.200"],
                        "subnetId": external_subnets_id[1]
                    }]
                }
            }]
        }]
    }
    return ext_cps_vdu2_cp2_in_num_dynamic


def _set_ext_virtual_link_cp2(networks_id, external_subnets_id):
    ext_virtual_link_cp2 = {
        "id": uuidsentinel.evl2_id,
        "resourceId": networks_id[1],
        "extCps": [
            _set_ext_cps_vdu1_cp2(external_subnets_id),
            _set_ext_cps_vdu2_cp2(external_subnets_id)
        ]
    }
    return ext_virtual_link_cp2


def _set_ext_virtual_link_cp2_in_num_dynamic(networks_id, external_subnets_id):
    ext_virtual_link_cp2_in_num_dynamic = {
        "id": uuidsentinel.evl2_id,
        "resourceId": networks_id[1],
        "extCps": [
            _set_ext_cps_vdu1_cp2_in_num_dynamic(external_subnets_id),
            _set_ext_cps_vdu2_cp2_in_num_dynamic(external_subnets_id)
        ]
    }
    return ext_virtual_link_cp2_in_num_dynamic


def _set_ext_mng_vtl_lnks(ext_mngd_networks_id):
    ext_mng_vtl_lnks = [{
        "id": uuidsentinel.emvl1_id,
        "vnfVirtualLinkDescId": "internalVL1",
        "resourceId": ext_mngd_networks_id[0]
    }, {
        "id": uuidsentinel.emvl2_id,
        "vnfVirtualLinkDescId": "internalVL2",
        "resourceId": ext_mngd_networks_id[1]
    }]
    return ext_mng_vtl_lnks


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
        data = {
            "flavourId": "simple",
            "instantiationLevelId": "instantiation_level_1",
            "extVirtualLinks": [
                _set_ext_virtual_link_cp1(
                    networks_id, external_ports_id),
                _set_ext_virtual_link_cp2(
                    networks_id, external_subnets_id)
            ],
            "extManagedVirtualLinks": _set_ext_mng_vtl_lnks(
                ext_mngd_networks_id),
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
    def make_inst_request_body_include_num_dynamic(
            tenant_id,
            networks_id,
            ext_mngd_networks_id,
            external_ports_id,
            external_subnets_id):
        data = {
            "flavourId": "simple",
            "instantiationLevelId": "instantiation_level_1",
            "extVirtualLinks": [
                _set_ext_virtual_link_cp1(networks_id, external_ports_id),
                _set_ext_virtual_link_cp2_in_num_dynamic(
                    networks_id, external_subnets_id)
            ],
            "extManagedVirtualLinks": _set_ext_mng_vtl_lnks(
                ext_mngd_networks_id),
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

    @staticmethod
    def make_change_ext_conn_request_body(
            tenant_id,
            networks_id,
            external_subnets_id):

        # set external subnet_id on vim.
        ext_cps_vdu2_cp2 = {
            "cpdId": "VDU2_CP2",
            "cpConfig": [{
                "cpProtocolData": [{
                    "layerProtocol": "IP_OVER_ETHERNET",
                    "ipOverEthernet": {
                        "ipAddresses": [{
                            "type": "IPV4",
                            "fixedAddresses": ["22.22.2.200"],
                            "subnetId": external_subnets_id[0]
                        }]
                    }
                }]
            }]
        }

        ext_virtual_link_cp2 = {
            "id": uuidsentinel.evl2_id,
            "resourceId": networks_id[0],
            "extCps": [
                ext_cps_vdu2_cp2
            ]
        }

        data = {
            "extVirtualLinks": [
                ext_virtual_link_cp2
            ],
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
        }

        return data
