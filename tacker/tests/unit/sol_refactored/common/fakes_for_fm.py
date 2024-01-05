# Copyright (C) 2022 Fujitsu
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


alarm_example = {
    "id": "78a39661-60a8-4824-b989-88c1b0c3534a",
    "managedObjectId": "c61314d0-f583-4ab3-a457-46426bce02d3",
    "rootCauseFaultyResource": {
        "faultyResource": {
            "vimConnectionId": "vim1",
            "resourceId": "4e6ccbe1-38ec-4b1b-a278-64de09ba01b3",
            "vimLevelResourceType": "OS::Nova::Server"
        },
        "faultyResourceType": "COMPUTE"
    },
    "alarmRaisedTime": "2021-09-06T10:21:03Z",
    "alarmChangedTime": "2021-09-06T10:21:03Z",
    "alarmClearedTime": "2021-09-06T10:21:03Z",
    "alarmAcknowledgedTime": "2021-09-06T10:21:03Z",
    "ackState": "UNACKNOWLEDGED",
    "perceivedSeverity": "WARNING",
    "eventTime": "2021-09-06T10:21:03Z",
    "eventType": "EQUIPMENT_ALARM",
    "faultType": "Fault Type",
    "probableCause": "The server cannot be connected.",
    "isRootCause": False,
    "correlatedAlarmIds": [
        "c88b624e-e997-4b17-b674-10ca2bab62e0",
        "c16d41fd-12e2-49a6-bb17-72faf702353f"
    ],
    "faultDetails": [
        "Fault",
        "Details"
    ],
    "_links": {
        "self": {
            "href": "/vnffm/v1/alarms/78a39661-60a8-4824-b989-88c1b0c3534a"
        },
        "objectInstance": {
            "href": "/vnflcm/v1/vnf_instances/"
                    "0e5f3086-4e79-47ed-a694-54c29155fa26"
        }
    }
}

fm_subsc_example = {
    "id": "78a39661-60a8-4824-b989-88c1b0c3534a",
    "filter": {
        "vnfInstanceSubscriptionFilter": {
            "vnfdIds": [
                "dummy-vnfdId-1"
            ],
            "vnfProductsFromProviders": [
                {
                    "vnfProvider": "dummy-vnfProvider-1",
                    "vnfProducts": [
                        {
                            "vnfProductName": "dummy-vnfProductName-1-1",
                            "versions": [
                                {
                                    "vnfSoftwareVersion": '1.0',
                                    "vnfdVersions": ['1.0', '2.0']
                                }
                            ]
                        }
                    ]
                }
            ],
            "vnfInstanceIds": [
                "dummy-vnfInstanceId-1"
            ],
            "vnfInstanceNames": [
                "dummy-vnfInstanceName-1"
            ]
        },
        "notificationTypes": [
            "AlarmNotification",
            "AlarmClearedNotification"
        ],
        "faultyResourceTypes": [
            "COMPUTE"
        ],
        "perceivedSeverities": [
            "WARNING"
        ],
        "eventTypes": [
            "EQUIPMENT_ALARM"
        ],
        "probableCauses": [
            "The server cannot be connected."
        ]
    },
    "callbackUri": "/nfvo/notify/alarm",
    "_links": {
        "self": {
            "href": "/vnffm/v1/subscriptions/"
                    "78a39661-60a8-4824-b989-88c1b0c3534a"
        }
    }
}
